#!/usr/bin/env python3
"""
DataSync 远程数据清理管理器
负责清理远程数据库中的过期数据，释放存储空间
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import text, select, func

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from models import CleanupLog
from logs.logger import DataSyncLogger
from monitoring.monitor_client import get_monitor_client


class CleanupManager:
    """远程数据清理管理器"""
    
    def __init__(self, config_manager, monitor_client=None):
        """
        初始化清理管理器
        
        Args:
            config_manager: 配置管理器实例
            monitor_client: 监控客户端实例（可选）
        """
        self.config = config_manager
        self.cleanup_config = config_manager.get_cleanup_config()
        self.logger = DataSyncLogger(logging.getLogger('datasync.cleanup'))
        
        # 监控客户端
        self.monitor = monitor_client or get_monitor_client()
        
        # 清理配置参数
        self.enabled = self.cleanup_config.get('enabled', True)
        self.retention_days = self.cleanup_config.get('retention_days', 60)
        self.batch_size = self.cleanup_config.get('batch_size', 5000)
        self.max_delete_per_day = self.cleanup_config.get('max_delete_per_day', 100000)
        self.safety_check = self.cleanup_config.get('safety_check', True)
        
        # 数据库管理器
        self.db_manager = None
        
        # 清理状态
        self.is_running = False
        self.daily_deleted_count = 0
    
    async def initialize(self):
        """初始化清理管理器"""
        self.logger.info("初始化清理管理器")
        
        if not self.enabled:
            self.logger.info("远程数据清理功能已禁用")
            return
        
        # 初始化数据库管理器
        local_config = self.config.get_database_config('local')
        remote_config = self.config.get_database_config('remote')
        
        self.db_manager = DatabaseManager(local_config, remote_config)
        await self.db_manager.initialize()
        
        # 检查今日删除计数
        await self._load_daily_deleted_count()
        
        self.logger.info("清理管理器初始化完成")
    
    async def run(self, dry_run: bool = False):
        """
        运行远程数据清理
        
        Args:
            dry_run: 是否为预览模式
        """
        if not self.enabled:
            self.logger.info("远程数据清理功能已禁用")
            return
        
        if self.is_running:
            self.logger.warning("清理任务已在运行中")
            return
        
        self.is_running = True
        start_time = time.time()
        total_deleted = 0
        
        try:
            self.logger.cleanup_start(dry_run=dry_run)
            
            # 发出清理开始事件
            await self.monitor.emit_event(
                event_type="cleanup_start",
                level="info",
                message=f"开始远程数据清理 (dry_run: {dry_run})",
                details={
                    "dry_run": dry_run,
                    "retention_days": self.retention_days,
                    "daily_deleted_count": self.daily_deleted_count
                }
            )
            
            # 检查今日删除限制
            if self.daily_deleted_count >= self.max_delete_per_day:
                self.logger.warning(f"今日删除数量已达限制: {self.daily_deleted_count}/{self.max_delete_per_day}")
                return
            
            # 安全检查
            if self.safety_check and not dry_run:
                safety_passed = await self._perform_safety_check()
                if not safety_passed:
                    self.logger.error("安全检查失败，跳过清理")
                    return
            
            # 计算清理时间范围
            cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
            
            # 清理各个表的数据
            tables_to_clean = ['coin_data', 'indicator_data']
            
            for table_name in tables_to_clean:
                deleted_count = await self._cleanup_table_data(table_name, cutoff_date, dry_run)
                total_deleted += deleted_count
                
                # 检查删除限制
                if self.daily_deleted_count + deleted_count >= self.max_delete_per_day:
                    self.logger.warning("达到每日删除限制，停止清理")
                    break
            
            duration = time.time() - start_time
            
            if not dry_run:
                self.daily_deleted_count += total_deleted
                await self._log_cleanup_completion(cutoff_date, total_deleted, duration)
            
            self.logger.cleanup_complete(duration, total_deleted)
            
            # 发出清理成功事件
            await self.monitor.cleanup_success(total_deleted, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"数据清理失败: {e}", exc_info=True)
            
            # 发出清理失败事件
            await self.monitor.cleanup_failure(str(e))
            
            if not dry_run:
                await self._log_cleanup_error(e, duration)
            raise
        finally:
            self.is_running = False
    
    async def _perform_safety_check(self) -> bool:
        """
        执行安全检查，确保本地数据完整性
        
        Returns:
            安全检查是否通过
        """
        self.logger.info("执行清理前安全检查")
        
        try:
            # 检查本地数据库连接
            local_health = await self.db_manager.health_check()
            if local_health['local_db']['status'] != 'healthy':
                self.logger.error("本地数据库不健康，跳过清理")
                return False
            
            # 检查关键表的数据完整性
            for table_name in ['coin_data', 'indicator_data']:
                local_info = await self.db_manager.get_local_table_info(table_name)
                if local_info['row_count'] == 0:
                    self.logger.warning(f"本地表 {table_name} 为空，跳过清理")
                    return False
            
            self.logger.info("安全检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"安全检查失败: {e}")
            return False
    
    async def _cleanup_table_data(self, table_name: str, cutoff_date: datetime, dry_run: bool = False) -> int:
        """
        清理指定表的过期数据
        
        Args:
            table_name: 表名
            cutoff_date: 截止日期
            dry_run: 是否为预览模式
            
        Returns:
            删除的记录数
        """
        self.logger.info(f"开始清理表 {table_name}，截止日期: {cutoff_date}")
        
        # 首先查询需要删除的记录数
        count_query = f"""
        SELECT COUNT(*) FROM {table_name} 
        WHERE time < :cutoff_date
        """
        
        result = await self.db_manager.execute_remote(count_query, {'cutoff_date': cutoff_date})
        total_to_delete = result.scalar()
        
        if total_to_delete == 0:
            self.logger.info(f"表 {table_name} 没有需要清理的数据")
            return 0
        
        self.logger.info(f"表 {table_name} 需要清理 {total_to_delete} 条记录")
        
        if dry_run:
            return total_to_delete
        
        # 分批删除数据
        total_deleted = 0
        remaining = min(total_to_delete, self.max_delete_per_day - self.daily_deleted_count)
        
        while remaining > 0 and total_deleted < remaining:
            batch_size = min(self.batch_size, remaining - total_deleted)
            
            # 删除一批数据
            delete_query = f"""
            DELETE FROM {table_name} 
            WHERE time < :cutoff_date 
            AND ctid IN (
                SELECT ctid FROM {table_name} 
                WHERE time < :cutoff_date 
                LIMIT :batch_size
            )
            """
            
            try:
                async with self.db_manager.get_remote_session() as session:
                    result = await session.execute(
                        text(delete_query), 
                        {
                            'cutoff_date': cutoff_date,
                            'batch_size': batch_size
                        }
                    )
                    batch_deleted = result.rowcount
                    await session.commit()
                
                total_deleted += batch_deleted
                self.logger.debug(f"表 {table_name} 已删除 {batch_deleted} 条记录")
                
                if batch_deleted == 0:
                    break
                
                # 避免过于频繁的操作
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"删除表 {table_name} 数据时出错: {e}")
                break
        
        self.logger.info(f"表 {table_name} 清理完成，删除了 {total_deleted} 条记录")
        return total_deleted
    
    async def _load_daily_deleted_count(self):
        """加载今日删除计数"""
        today = datetime.utcnow().date()
        
        try:
            async with self.db_manager.get_local_session() as session:
                result = await session.execute(
                    select(func.sum(CleanupLog.records_deleted))
                    .where(func.date(CleanupLog.cleanup_time) == today)
                    .where(CleanupLog.cleanup_status == 'completed')
                )
                
                count = result.scalar()
                self.daily_deleted_count = count if count else 0
                
        except Exception as e:
            self.logger.warning(f"加载每日删除计数失败: {e}")
            self.daily_deleted_count = 0
    
    async def _log_cleanup_completion(self, cutoff_date: datetime, records_deleted: int, duration: float):
        """记录清理完成日志"""
        log_entry = CleanupLog(
            cleanup_time=datetime.utcnow(),
            records_deleted=records_deleted,
            cleanup_status='completed',
            time_range_start=datetime.min.replace(tzinfo=None),
            time_range_end=cutoff_date
        )
        
        async with self.db_manager.get_local_session() as session:
            session.add(log_entry)
            await session.commit()
    
    async def _log_cleanup_error(self, error: Exception, duration: float):
        """记录清理错误日志"""
        log_entry = CleanupLog(
            cleanup_time=datetime.utcnow(),
            records_deleted=0,
            cleanup_status='failed',
            error_message=str(error)
        )
        
        async with self.db_manager.get_local_session() as session:
            session.add(log_entry)
            await session.commit()
    
    async def get_cleanup_status(self) -> Dict[str, Any]:
        """
        获取清理状态
        
        Returns:
            清理状态字典
        """
        status = {
            'enabled': self.enabled,
            'is_running': self.is_running,
            'daily_deleted_count': self.daily_deleted_count,
            'max_delete_per_day': self.max_delete_per_day,
            'config': {
                'retention_days': self.retention_days,
                'batch_size': self.batch_size,
                'safety_check': self.safety_check
            }
        }
        
        if self.db_manager:
            # 获取最近的清理日志
            try:
                async with self.db_manager.get_local_session() as session:
                    recent_logs = await session.execute(
                        select(CleanupLog)
                        .order_by(CleanupLog.created_at.desc())
                        .limit(5)
                    )
                    
                    status['recent_logs'] = [log.to_dict() for log in recent_logs.scalars()]
            except Exception as e:
                self.logger.warning(f"获取清理日志失败: {e}")
                status['recent_logs'] = []
        
        return status
    
    async def close(self):
        """关闭清理管理器"""
        self.logger.info("关闭清理管理器")
        
        if self.db_manager:
            await self.db_manager.close()