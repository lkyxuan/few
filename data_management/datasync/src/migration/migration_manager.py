#!/usr/bin/env python3
"""
DataSync 数据迁移管理器
负责在不同存储层之间迁移数据（热数据→温数据→冷数据）
"""

import asyncio
import logging
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from sqlalchemy import text, select, func

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from models import MigrationLog
from logs.logger import DataSyncLogger
from monitoring.monitor_client import get_monitor_client


class MigrationManager:
    """数据迁移管理器"""
    
    def __init__(self, config_manager, monitor_client=None):
        """
        初始化迁移管理器
        
        Args:
            config_manager: 配置管理器实例
            monitor_client: 监控客户端实例（可选）
        """
        self.config = config_manager
        self.migration_config = config_manager.get_migration_config()
        self.storage_config = config_manager.get_storage_config()
        self.logger = DataSyncLogger(logging.getLogger('datasync.migration'))
        
        # 监控客户端
        self.monitor = monitor_client or get_monitor_client()
        
        # 迁移配置参数
        self.enabled = self.migration_config.get('enabled', True)
        self.hot_retention_days = self.migration_config.get('hot_retention_days', 365)
        self.warm_retention_days = self.migration_config.get('warm_retention_days', 1460)
        self.batch_size = self.migration_config.get('batch_size', 10000)
        self.parallel_jobs = self.migration_config.get('parallel_jobs', 2)
        
        # 存储路径
        self.hot_data_path = Path(self.storage_config.get('hot_data_path', '/databao_hot'))
        self.warm_data_path = Path(self.storage_config.get('warm_data_path', '/databao_warm'))
        self.cold_data_path = Path(self.storage_config.get('cold_data_path', '/databao_cold'))
        
        # 数据库管理器
        self.db_manager = None
        
        # 迁移状态
        self.is_running = False
    
    async def initialize(self):
        """初始化迁移管理器"""
        self.logger.info("初始化迁移管理器")
        
        if not self.enabled:
            self.logger.info("数据迁移功能已禁用")
            return
        
        # 初始化数据库管理器
        local_config = self.config.get_database_config('local')
        remote_config = self.config.get_database_config('remote')
        
        self.db_manager = DatabaseManager(local_config, remote_config)
        await self.db_manager.initialize()
        
        # 检查存储路径
        self._check_storage_paths()
        
        self.logger.info("迁移管理器初始化完成")
    
    async def run(self, dry_run: bool = False):
        """
        运行数据迁移
        
        Args:
            dry_run: 是否为预览模式
        """
        if not self.enabled:
            self.logger.info("数据迁移功能已禁用")
            return
        
        if self.is_running:
            self.logger.warning("迁移任务已在运行中")
            return
        
        self.is_running = True
        start_time = time.time()
        
        try:
            self.logger.migration_start("定期数据迁移", dry_run=dry_run)
            
            # 发出迁移开始事件
            await self.monitor.emit_event(
                event_type="migration_start",
                level="info",
                message=f"开始数据迁移 (dry_run: {dry_run})",
                details={
                    "dry_run": dry_run,
                    "hot_retention_days": self.hot_retention_days,
                    "warm_retention_days": self.warm_retention_days
                }
            )
            
            # 执行迁移任务
            migration_results = await self._execute_migration_tasks(dry_run)
            
            # 汇总迁移结果
            total_migrated = sum(result['records_migrated'] for result in migration_results)
            duration = time.time() - start_time
            
            self.logger.migration_complete("定期数据迁移", duration, total_migrated)
            
            # 发出迁移成功事件
            await self.monitor.migration_success("data_lifecycle", total_migrated, duration)
            
            # 记录迁移日志
            if not dry_run:
                await self._log_migration_completion(migration_results, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"数据迁移失败: {e}", exc_info=True)
            
            # 发出迁移失败事件
            await self.monitor.migration_failure("data_lifecycle", str(e))
            
            if not dry_run:
                await self._log_migration_error("定期数据迁移", e)
            raise
        finally:
            self.is_running = False
    
    async def _execute_migration_tasks(self, dry_run: bool) -> List[Dict[str, Any]]:
        """
        执行迁移任务
        
        Args:
            dry_run: 是否为预览模式
            
        Returns:
            迁移结果列表
        """
        tasks = []
        
        # 热数据 → 温数据迁移
        tasks.append(self._migrate_hot_to_warm(dry_run))
        
        # 温数据 → 冷数据迁移
        tasks.append(self._migrate_warm_to_cold(dry_run))
        
        # 并发执行迁移任务（最多parallel_jobs个）
        semaphore = asyncio.Semaphore(self.parallel_jobs)
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[bounded_task(task) for task in tasks], 
            return_exceptions=True
        )
        
        # 处理结果和异常
        migration_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"迁移任务{i}失败: {result}")
                migration_results.append({
                    'task': f'migration_task_{i}',
                    'status': 'failed',
                    'records_migrated': 0,
                    'error': str(result)
                })
            else:
                migration_results.append(result)
        
        return migration_results
    
    async def _migrate_hot_to_warm(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        热数据迁移到温数据
        
        Args:
            dry_run: 是否为预览模式
            
        Returns:
            迁移结果字典
        """
        migration_type = "hot_to_warm"
        start_time = time.time()
        
        self.logger.info("开始热数据到温数据迁移")
        
        try:
            # 计算迁移时间点
            cutoff_date = datetime.utcnow() - timedelta(days=self.hot_retention_days)
            
            # 迁移各个表的数据
            total_migrated = 0
            tables_to_migrate = ['coin_data', 'indicator_data']
            
            for table_name in tables_to_migrate:
                migrated_count = await self._migrate_table_data(
                    table_name, 
                    f"{table_name}_hot", 
                    f"{table_name}_warm",
                    cutoff_date, 
                    dry_run
                )
                total_migrated += migrated_count
            
            duration = time.time() - start_time
            return {
                'migration_type': migration_type,
                'status': 'completed',
                'records_migrated': total_migrated,
                'duration': duration,
                'cutoff_date': cutoff_date
            }
            
        except Exception as e:
            self.logger.error(f"热数据到温数据迁移失败: {e}")
            raise
    
    async def _migrate_warm_to_cold(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        温数据迁移到冷数据
        
        Args:
            dry_run: 是否为预览模式
            
        Returns:
            迁移结果字典
        """
        migration_type = "warm_to_cold"
        start_time = time.time()
        
        self.logger.info("开始温数据到冷数据迁移")
        
        try:
            # 计算迁移时间点
            cutoff_date = datetime.utcnow() - timedelta(days=self.warm_retention_days)
            
            # 迁移各个表的数据
            total_migrated = 0
            tables_to_migrate = ['coin_data', 'indicator_data']
            
            for table_name in tables_to_migrate:
                migrated_count = await self._migrate_table_data(
                    table_name,
                    f"{table_name}_warm",
                    f"{table_name}_cold", 
                    cutoff_date,
                    dry_run
                )
                total_migrated += migrated_count
            
            duration = time.time() - start_time
            return {
                'migration_type': migration_type,
                'status': 'completed', 
                'records_migrated': total_migrated,
                'duration': duration,
                'cutoff_date': cutoff_date
            }
            
        except Exception as e:
            self.logger.error(f"温数据到冷数据迁移失败: {e}")
            raise
    
    async def _migrate_table_data(
        self, 
        base_table: str, 
        source_partition: str, 
        target_partition: str,
        cutoff_date: datetime,
        dry_run: bool = False
    ) -> int:
        """
        迁移表数据
        
        Args:
            base_table: 基础表名
            source_partition: 源分区
            target_partition: 目标分区
            cutoff_date: 截止日期
            dry_run: 是否为预览模式
            
        Returns:
            迁移的记录数
        """
        self.logger.info(f"迁移 {source_partition} → {target_partition}，截止日期: {cutoff_date}")
        
        # 查询需要迁移的记录数
        count_query = f"""
        SELECT COUNT(*) FROM {source_partition} 
        WHERE time < :cutoff_date
        """
        
        result = await self.db_manager.execute_local(count_query, {'cutoff_date': cutoff_date})
        total_to_migrate = result.scalar()
        
        if total_to_migrate == 0:
            self.logger.info(f"分区 {source_partition} 没有需要迁移的数据")
            return 0
        
        self.logger.info(f"分区 {source_partition} 需要迁移 {total_to_migrate} 条记录")
        
        if dry_run:
            return total_to_migrate
        
        # 分批迁移数据
        total_migrated = 0
        
        while total_migrated < total_to_migrate:
            batch_size = min(self.batch_size, total_to_migrate - total_migrated)
            
            try:
                async with self.db_manager.get_local_session() as session:
                    # 插入数据到目标分区
                    insert_query = f"""
                    INSERT INTO {target_partition}
                    SELECT * FROM {source_partition}
                    WHERE time < :cutoff_date
                    LIMIT :batch_size
                    """
                    
                    result = await session.execute(
                        text(insert_query),
                        {
                            'cutoff_date': cutoff_date,
                            'batch_size': batch_size
                        }
                    )
                    
                    inserted_count = result.rowcount
                    
                    if inserted_count > 0:
                        # 删除源分区中已迁移的数据
                        delete_query = f"""
                        DELETE FROM {source_partition}
                        WHERE time < :cutoff_date
                        AND ctid IN (
                            SELECT ctid FROM {source_partition}
                            WHERE time < :cutoff_date
                            LIMIT :batch_size
                        )
                        """
                        
                        await session.execute(
                            text(delete_query),
                            {
                                'cutoff_date': cutoff_date,
                                'batch_size': batch_size
                            }
                        )
                    
                    await session.commit()
                    total_migrated += inserted_count
                    
                    self.logger.debug(f"已迁移 {inserted_count} 条记录")
                    
                    if inserted_count == 0:
                        break
                
                # 避免过于频繁的操作
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"迁移数据时出错: {e}")
                break
        
        self.logger.info(f"分区迁移完成: {source_partition} → {target_partition}，迁移了 {total_migrated} 条记录")
        return total_migrated
    
    def _check_storage_paths(self):
        """检查存储路径"""
        paths = [
            (self.hot_data_path, "热数据"),
            (self.warm_data_path, "温数据"),
            (self.cold_data_path, "冷数据")
        ]
        
        for path, name in paths:
            if not path.exists():
                self.logger.warning(f"{name}存储路径不存在: {path}")
            else:
                # 检查可用空间
                stats = shutil.disk_usage(path)
                free_gb = stats.free / (1024**3)
                self.logger.info(f"{name}存储({path}): {free_gb:.1f}GB可用空间")
    
    async def _log_migration_completion(self, migration_results: List[Dict], duration: float):
        """记录迁移完成日志"""
        for result in migration_results:
            if result.get('status') == 'completed':
                log_entry = MigrationLog(
                    migration_type=result['migration_type'],
                    migration_time=datetime.utcnow(),
                    records_migrated=result['records_migrated'],
                    migration_status='completed',
                    source_partition=result['migration_type'].split('_to_')[0],
                    target_partition=result['migration_type'].split('_to_')[1]
                )
                
                async with self.db_manager.get_local_session() as session:
                    session.add(log_entry)
                    await session.commit()
    
    async def _log_migration_error(self, migration_type: str, error: Exception):
        """记录迁移错误日志"""
        log_entry = MigrationLog(
            migration_type=migration_type,
            migration_time=datetime.utcnow(),
            records_migrated=0,
            migration_status='failed',
            source_partition='unknown',
            target_partition='unknown'
        )
        
        async with self.db_manager.get_local_session() as session:
            session.add(log_entry)
            await session.commit()
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """
        获取迁移状态
        
        Returns:
            迁移状态字典
        """
        status = {
            'enabled': self.enabled,
            'is_running': self.is_running,
            'config': {
                'hot_retention_days': self.hot_retention_days,
                'warm_retention_days': self.warm_retention_days,
                'batch_size': self.batch_size,
                'parallel_jobs': self.parallel_jobs
            },
            'storage_paths': {
                'hot_data_path': str(self.hot_data_path),
                'warm_data_path': str(self.warm_data_path),
                'cold_data_path': str(self.cold_data_path)
            }
        }
        
        # 检查存储空间
        for path_name, path in status['storage_paths'].items():
            try:
                path_obj = Path(path)
                if path_obj.exists():
                    stats = shutil.disk_usage(path_obj)
                    status[f'{path_name}_free_gb'] = stats.free / (1024**3)
                else:
                    status[f'{path_name}_free_gb'] = None
            except Exception:
                status[f'{path_name}_free_gb'] = None
        
        if self.db_manager:
            # 获取最近的迁移日志
            try:
                async with self.db_manager.get_local_session() as session:
                    recent_logs = await session.execute(
                        select(MigrationLog)
                        .order_by(MigrationLog.created_at.desc())
                        .limit(5)
                    )
                    
                    status['recent_logs'] = [log.to_dict() for log in recent_logs.scalars()]
            except Exception as e:
                self.logger.warning(f"获取迁移日志失败: {e}")
                status['recent_logs'] = []
        
        return status
    
    async def close(self):
        """关闭迁移管理器"""
        self.logger.info("关闭迁移管理器")
        
        if self.db_manager:
            await self.db_manager.close()