#!/usr/bin/env python3
"""
DataSync 同步管理器
负责从远程数据库同步数据到本地数据库的核心逻辑
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text, select, func
from sqlalchemy.dialects.postgresql import insert

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.connection import DatabaseManager
from models import CoinData, SyncLog
from logs.logger import DataSyncLogger
from monitoring.monitor_client import get_monitor_client


class SyncManager:
    """数据同步管理器"""
    
    def __init__(self, config_manager, monitor_client=None):
        """
        初始化同步管理器
        
        Args:
            config_manager: 配置管理器实例
            monitor_client: 监控客户端实例（可选）
        """
        self.config = config_manager
        self.sync_config = config_manager.get_sync_config()
        self.logger = DataSyncLogger(logging.getLogger('datasync.sync'))
        
        # 监控客户端
        self.monitor = monitor_client or get_monitor_client()
        
        # 移除触发文件管理器，现在使用PostgreSQL NOTIFY机制
        
        # 同步配置参数 - 优化版
        self.batch_size = self.sync_config.get('batch_size', 10000)  # 提升到10,000条批量查询
        self.insert_batch_size = self.sync_config.get('insert_batch_size', 1000)  # 保持1,000条插入批次
        self.concurrent_workers = self.sync_config.get('concurrent_workers', 10)  # 增加并发worker数量
        self.retry_max = self.sync_config.get('retry_max', 3)
        
        # 数据库管理器
        self.db_manager = None
        
        # 同步状态
        self.is_running = False
        self.last_sync_times = {}
    
    async def initialize(self):
        """初始化同步管理器"""
        self.logger.info("初始化同步管理器")
        
        # 初始化数据库管理器
        local_config = self.config.get_database_config('local')
        remote_config = self.config.get_database_config('remote')
        
        self.db_manager = DatabaseManager(local_config, remote_config)
        await self.db_manager.initialize()
        
        # 加载上次同步时间
        await self._load_last_sync_times()
        
        self.logger.info("同步管理器初始化完成")
    
    async def run(self, dry_run: bool = False):
        """
        运行数据同步
        
        Args:
            dry_run: 是否为预览模式
        """
        if self.is_running:
            self.logger.warning("同步任务已在运行中")
            return
        
        self.is_running = True
        start_time = time.time()
        
        try:
            self.logger.sync_start("数据同步", dry_run=dry_run)
            
            # 发出同步开始事件
            await self.monitor.sync_started("coin_data", 0)
            
            # 发出同步状态信息
            await self.monitor.service_status(
                message="🚀 开始数据同步检查",
                details={
                    "action": "sync_check_start", 
                    "dry_run": dry_run
                }
            )
            
            # 执行同步任务
            sync_results = await self._execute_sync_tasks(dry_run)
            
            # 汇总同步结果
            total_records = sum(result.get('records_synced', 0) for result in sync_results)
            duration = time.time() - start_time
            
            self.logger.sync_complete("数据同步", duration, total_records, 
                                    tasks_completed=len(sync_results))
            
            # 发出同步成功事件 - 显示具体表名和时间信息（不再创建触发文件，已在批次中创建）
            for result in sync_results:
                if result.get('status') == 'completed' and result.get('records_synced', 0) > 0:
                    table_name = result.get('table', 'unknown_table')
                    await self.monitor.sync_success(table_name, result.get('records_synced', 0), duration)
                    self.logger.info(f"同步任务完成: {table_name} 总计{result.get('records_synced', 0):,}条记录")
            
            # 记录同步日志
            if not dry_run:
                await self._log_sync_completion(sync_results, duration)
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.sync_error("数据同步", e, duration=duration)
            
            # 发出同步失败事件
            await self.monitor.sync_failure("all_tables", str(e), duration)
            
            if not dry_run:
                await self._log_sync_error("数据同步", e)
            raise
        finally:
            self.is_running = False
    
    async def _execute_sync_tasks(self, dry_run: bool) -> List[Dict[str, Any]]:
        """
        执行所有同步任务
        
        Args:
            dry_run: 是否为预览模式
            
        Returns:
            同步结果列表
        """
        tasks = []
        
        # 检查远程数据库中存在的表
        remote_tables = await self._get_remote_tables()
        self.logger.info(f"远程数据库中发现的表: {remote_tables}")
        
        # 创建币种数据同步任务（如果存在）
        if 'coin_data' in remote_tables:
            tasks.append(self._sync_coin_data(dry_run))
        else:
            self.logger.warning("远程数据库中没有coin_data表")
        
        
        if not tasks:
            self.logger.warning("没有可同步的表")
            return []
        
        # 并发执行同步任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果和异常
        sync_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"同步任务{i}失败: {result}")
                sync_results.append({
                    'task': f'task_{i}',
                    'status': 'failed',
                    'records_synced': 0,
                    'error': str(result)
                })
            else:
                sync_results.append(result)
        
        return sync_results
    
    async def _get_remote_tables(self) -> List[str]:
        """
        获取远程数据库中的表列表
        
        Returns:
            表名列表
        """
        try:
            query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
            """
            result = await self.db_manager.execute_remote(query, {})
            tables = [row[0] for row in result.fetchall()]
            return tables
        except Exception as e:
            self.logger.error(f"获取远程表列表失败: {e}")
            return []
    
    async def _sync_coin_data(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        同步币种数据
        
        Args:
            dry_run: 是否为预览模式
            
        Returns:
            同步结果字典
        """
        table_name = 'coin_data'
        start_time = time.time()
        
        self.logger.info(f"开始同步{table_name}")
        
        try:
            # 获取上次同步时间
            last_sync_time = self.last_sync_times.get(table_name)
            
            # 查询需要同步的数据量
            total_records = await self._get_remote_records_count(table_name, last_sync_time)
            
            # 无论是否有数据都发送状态通知
            await self.monitor.service_status(
                message=f"📊 数据库同步状态检查完成",
                details={
                    "table": table_name,
                    "records_to_sync": total_records,
                    "last_sync_time": str(last_sync_time) if last_sync_time else "首次同步"
                },
                metrics={
                    "records_to_sync": total_records
                }
            )
            
            if total_records == 0:
                return {
                    'table': table_name,
                    'status': 'completed',
                    'records_synced': 0,
                    'duration': time.time() - start_time
                }
            
            self.logger.info(f"{table_name}需要同步{total_records}条记录")
            
            if dry_run:
                return {
                    'table': table_name,
                    'status': 'preview',
                    'records_to_sync': total_records,
                    'duration': time.time() - start_time
                }
            
            # 执行分批同步
            records_synced, latest_sync_time = await self._sync_table_data(table_name, last_sync_time)
            
            # 更新同步时间
            if latest_sync_time:
                await self._update_last_sync_time(table_name, latest_sync_time)
            else:
                current_time = datetime.utcnow()
                await self._update_last_sync_time(table_name, current_time)
            
            duration = time.time() - start_time
            return {
                'table': table_name,
                'status': 'completed',
                'records_synced': records_synced,
                'duration': duration,
                'latest_sync_time': latest_sync_time
            }
            
        except Exception as e:
            self.logger.error(f"{table_name}同步失败: {e}")
            raise
    
    async def _get_remote_records_count(self, table_name: str, last_sync_time: Optional[datetime]) -> int:
        """
        获取远程数据库中需要同步的记录数
        
        Args:
            table_name: 表名
            last_sync_time: 上次同步时间
            
        Returns:
            记录数量
        """
        if last_sync_time:
            query = f"""
            SELECT COUNT(*) FROM {table_name} 
            WHERE time > :last_sync_time
            """
            params = {'last_sync_time': last_sync_time}
        else:
            query = f"SELECT COUNT(*) FROM {table_name}"
            params = {}
        
        result = await self.db_manager.execute_remote(query, params)
        return result.scalar()
    
    async def _sync_table_data(self, table_name: str, last_sync_time: Optional[datetime]) -> Tuple[int, Optional[datetime]]:
        """
        同步表数据 - 简化版本，确保数据完整性
        
        Args:
            table_name: 表名
            last_sync_time: 上次同步时间
            
        Returns:
            Tuple[同步的记录数, 最新同步时间]
        """
        total_synced = 0
        latest_time = None
        current_time = last_sync_time if last_sync_time else datetime(1970, 1, 1)
        
        self.logger.info(f"开始同步 {table_name}，起始时间: {current_time}")
        
        while True:
            # 查询一批数据
            query = f"""
            SELECT * FROM {table_name} 
            WHERE time >= :current_time
            ORDER BY time, coin_id
            LIMIT :limit
            """
            
            result = await self.db_manager.execute_remote(query, {
                'current_time': current_time,
                'limit': self.batch_size
            })
            rows = result.fetchall()
            
            if not rows:
                break
            
            # 插入数据
            batch_synced = await self._insert_batch_data(table_name, rows)
            total_synced += batch_synced
            
            # 更新游标
            last_row = rows[-1]
            latest_time = last_row[0]  # time字段
            current_time = latest_time
            
            # 发送通知
            if batch_synced > 0:
                await self._notify_datainsight_sync_done(table_name, batch_synced)
                await self.monitor.sync_progress(table_name, batch_synced, str(latest_time))
                self.logger.info(f"批次完成: {batch_synced:,}条，最新时间: {latest_time}")
            
            # 如果返回记录数小于批次大小，说明已同步完所有数据
            if len(rows) < self.batch_size:
                break
        
        return total_synced, latest_time
    
    async def _insert_batch_data(self, table_name: str, rows: List[Any]) -> int:
        """
        批量插入数据
        
        Args:
            table_name: 表名
            rows: 数据行列表
            
        Returns:
            插入的记录数
        """
        if not rows:
            return 0
        
        # 将行转换为字典
        data_list = []
        for row in rows:
            if hasattr(row, '_asdict'):
                data_list.append(row._asdict())
            elif hasattr(row, '_mapping'):
                data_list.append(dict(row._mapping))
            else:
                # 如果是tuple，需要配合column names
                data_list.append(dict(row))
        
        # 使用UPSERT语句处理重复数据
        if table_name == 'coin_data':
            insert_stmt = insert(CoinData.__table__).values(data_list)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['time', 'coin_id'],
                set_={
                    'current_price': insert_stmt.excluded.current_price,
                    'market_cap': insert_stmt.excluded.market_cap,
                    'total_volume': insert_stmt.excluded.total_volume,
                    'price_change_percentage_24h': insert_stmt.excluded.price_change_percentage_24h,
                    'last_updated': insert_stmt.excluded.last_updated
                }
            )
        else:
            raise ValueError(f"不支持的表名: {table_name}")
        
        # 执行插入
        async with self.db_manager.get_local_session() as session:
            await session.execute(upsert_stmt)
            await session.commit()
        
        return len(data_list)
    
    
    async def _load_last_sync_times(self):
        """加载上次同步时间 - 直接从数据表中获取最新时间"""
        async with self.db_manager.get_local_session() as session:
            # 查询每个表的最新数据时间（更可靠的方法）
            for table_name in ['coin_data']:
                try:
                    if table_name == 'coin_data':
                        # 直接查询coin_data表的最新时间
                        result = await session.execute(
                            text("SELECT MAX(time) FROM coin_data")
                        )
                    
                    row = result.fetchone()
                    if row and row[0]:
                        self.last_sync_times[table_name] = row[0]
                        self.logger.info(f"{table_name}本地最新时间: {row[0]}")
                    else:
                        self.logger.info(f"{table_name}表为空，将进行全量同步")
                        
                except Exception as e:
                    self.logger.warning(f"查询{table_name}最新时间失败: {e}，将进行全量同步")
    
    async def _update_last_sync_time(self, table_name: str, sync_time: datetime):
        """更新最后同步时间"""
        self.last_sync_times[table_name] = sync_time
    
    async def _log_sync_completion(self, sync_results: List[Dict], duration: float):
        """记录同步完成日志"""
        for result in sync_results:
            if result.get('status') == 'completed':
                log_entry = SyncLog(
                    sync_type=result['table'],
                    last_sync_time=datetime.utcnow(),
                    records_synced=result['records_synced'],
                    sync_status='completed'
                )
                
                async with self.db_manager.get_local_session() as session:
                    session.add(log_entry)
                    await session.commit()
    
    async def _log_sync_error(self, sync_type: str, error: Exception):
        """记录同步错误日志"""
        log_entry = SyncLog(
            sync_type=sync_type,
            last_sync_time=datetime.utcnow(),
            records_synced=0,
            sync_status='failed',
            error_message=str(error)
        )
        
        async with self.db_manager.get_local_session() as session:
            session.add(log_entry)
            await session.commit()
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态
        
        Returns:
            同步状态字典
        """
        status = {
            'is_running': self.is_running,
            'last_sync_times': self.last_sync_times.copy(),
            'config': {
                'batch_size': self.batch_size,
                'concurrent_workers': self.concurrent_workers,
                'retry_max': self.retry_max
            }
        }
        
        # 获取最近的同步日志
        async with self.db_manager.get_local_session() as session:
            recent_logs = await session.execute(
                select(SyncLog)
                .order_by(SyncLog.created_at.desc())
                .limit(10)
            )
            
            status['recent_logs'] = [log.to_dict() for log in recent_logs.scalars()]
        
        return status
    
    async def _notify_datainsight_sync_done(self, table_name: str, records_synced: int):
        """
        发送PostgreSQL通知给DataInsight
        
        Args:
            table_name: 表名
            records_synced: 同步的记录数
        """
        try:
            async with self.db_manager.get_local_session() as session:
                # 发送PostgreSQL通知
                await session.execute(
                    text("NOTIFY datainsight_wakeup, 'sync_done'")
                )
                await session.commit()
                
        except Exception as e:
            self.logger.error(f"发送PostgreSQL通知失败: {e}")
    
    async def close(self):
        """关闭同步管理器"""
        self.logger.info("关闭同步管理器")
        
        if self.db_manager:
            await self.db_manager.close()