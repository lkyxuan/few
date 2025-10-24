#!/usr/bin/env python3
"""
DataSync监控客户端
轻量级客户端，负责将监控事件发送到集中式监控服务
"""

import asyncio
import aiohttp
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional


class DataSyncMonitorClient:
    """DataSync监控客户端"""
    
    def __init__(self, service_name: str = "datasync", monitor_url: str = "http://localhost:9527"):
        """
        初始化监控客户端
        
        Args:
            service_name: 服务名称
            monitor_url: 监控服务URL
        """
        self.service_name = service_name
        self.monitor_url = monitor_url.rstrip('/')
        self.logger = logging.getLogger(f'{service_name}.monitor_client')
        
        # 连接配置
        self.timeout = 5  # 5秒超时
        self.retry_count = 2
        
        # 统计信息
        self.stats = {
            'events_sent': 0,
            'events_failed': 0,
            'last_success': None,
            'last_failure': None
        }
    
    async def emit_event(
        self,
        event_type: str,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送监控事件到集中监控服务
        
        Args:
            event_type: 事件类型 (如: sync_success, sync_failure, cleanup_success等)
            level: 事件级别 (info, warning, error, critical)
            message: 事件消息
            details: 详细信息字典
            metrics: 指标数据字典
            
        Returns:
            发送是否成功
        """
        payload = {
            "service": self.service_name,
            "event_type": event_type,
            "level": level,
            "message": message,
            "details": details or {},
            "metrics": metrics or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 立即输出到本地日志，确保用户能看到
        log_emoji = "✅" if event_type.endswith("_success") else "⚠️" if level == "warning" else "❌" if level == "error" else "ℹ️"
        self.logger.info(f"{log_emoji} {event_type}")
        self.logger.info(f"消息: {message}")
        self.logger.info(f"时间: {payload['timestamp']}")
        if metrics:
            self.logger.info(f"指标:")
            for k, v in metrics.items():
                self.logger.info(f"• {k}: {v}")
        
        # 异步发送到远程监控服务，避免阻塞业务逻辑
        asyncio.create_task(self._send_event_async(payload))
        return True  # 立即返回，不等待发送结果
    
    async def _send_event_async(self, payload: Dict[str, Any]):
        """异步发送事件"""
        for attempt in range(self.retry_count + 1):
            try:
                success = await self._do_send_event(payload)
                if success:
                    self.stats['events_sent'] += 1
                    self.stats['last_success'] = datetime.utcnow().isoformat()
                    if attempt > 0:
                        self.logger.info(f"事件发送成功 (重试 {attempt} 次): {payload['event_type']}")
                    return
                    
            except Exception as e:
                self.logger.warning(f"事件发送尝试 {attempt + 1} 失败: {e}")
                if attempt < self.retry_count:
                    await asyncio.sleep(1 * (attempt + 1))  # 递增延迟
        
        # 所有尝试都失败了
        self.stats['events_failed'] += 1
        self.stats['last_failure'] = datetime.utcnow().isoformat()
        self.logger.error(f"事件发送最终失败: {payload['event_type']} - {payload['message']}")
    
    async def _emit_event_sync(
        self,
        event_type: str,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        同步发送监控事件，等待结果（用于关键事件如进度通知）
        
        Args:
            event_type: 事件类型
            level: 事件级别
            message: 事件消息
            details: 详细信息字典
            metrics: 指标数据字典
            
        Returns:
            发送是否成功
        """
        payload = {
            "service": self.service_name,
            "event_type": event_type,
            "level": level,
            "message": message,
            "details": details or {},
            "metrics": metrics or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 立即输出到本地日志
        log_emoji = "📊" if event_type == "sync_progress" else "✅" if event_type.endswith("_success") else "⚠️" if level == "warning" else "❌" if level == "error" else "ℹ️"
        self.logger.info(f"{log_emoji} {event_type}")
        self.logger.info(f"消息: {message}")
        self.logger.info(f"时间: {payload['timestamp']}")
        if metrics:
            self.logger.info(f"指标:")
            for k, v in metrics.items():
                self.logger.info(f"• {k}: {v}")
        
        # 同步发送事件，重试机制确保可靠性
        for attempt in range(self.retry_count + 1):
            try:
                success = await self._do_send_event(payload)
                if success:
                    self.stats['events_sent'] += 1
                    self.stats['last_success'] = datetime.utcnow().isoformat()
                    if attempt > 0:
                        self.logger.info(f"同步事件发送成功 (重试 {attempt} 次): {event_type}")
                    return True
                    
            except Exception as e:
                self.logger.warning(f"同步事件发送尝试 {attempt + 1} 失败: {e}")
                if attempt < self.retry_count:
                    await asyncio.sleep(0.5 * (attempt + 1))  # 较短的延迟，因为是同步调用
        
        # 所有尝试都失败了
        self.stats['events_failed'] += 1
        self.stats['last_failure'] = datetime.utcnow().isoformat()
        self.logger.error(f"同步事件发送最终失败: {event_type} - {message}")
        return False
    
    async def _do_send_event(self, payload: Dict[str, Any]) -> bool:
        """执行事件发送"""
        url = f"{self.monitor_url}/api/events"
        
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('success', False)
                    else:
                        self.logger.warning(f"监控服务返回错误状态: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            self.logger.warning("监控服务连接超时")
            return False
        except aiohttp.ClientConnectorError:
            self.logger.warning("无法连接到监控服务")
            return False
        except Exception as e:
            self.logger.warning(f"发送监控事件异常: {e}")
            return False
    
    # 便捷方法：常用事件类型
    
    async def service_status(self, message: str, details: Dict[str, Any] = None, metrics: Dict[str, Any] = None):
        """服务状态事件"""
        await self.emit_event(
            event_type="service_status",
            level="info", 
            message=message,
            details=details or {},
            metrics=metrics or {}
        )
    
    async def sync_started(self, table_name: str, record_count: int = 0):
        """同步开始事件"""
        await self.emit_event(
            event_type="sync_start",
            level="info",
            message=f"开始同步表 {table_name}",
            details={"table": table_name},
            metrics={"expected_records": record_count}
        )
    
    async def sync_success(self, table_name: str, records_synced: int, duration: float):
        """同步成功事件"""
        await self.emit_event(
            event_type="sync_success",
            level="info", 
            message=f"同步表 {table_name} 成功，处理 {records_synced} 条记录",
            details={
                "table": table_name,
                "records_synced": records_synced,
                "duration_seconds": duration
            },
            metrics={
                "records_synced": records_synced,
                "duration": duration,
                "throughput": records_synced / max(duration, 1)
            }
        )
    
    async def sync_failure(self, table_name: str, error: str, duration: float = 0):
        """同步失败事件"""
        await self.emit_event(
            event_type="sync_failure",
            level="error",
            message=f"同步表 {table_name} 失败: {error}",
            details={
                "table": table_name,
                "error": error,
                "duration_seconds": duration
            },
            metrics={
                "duration": duration,
                "records_synced": 0
            }
        )
    
    async def sync_progress(self, table_name: str, records_synced: int, latest_time: str = None):
        """同步进度事件 - 每批次发送进度更新"""
        message = f"同步表 {table_name} 进度: {records_synced:,} 条记录"
        if latest_time and latest_time != 'None':
            message += f"（最新数据: {latest_time}）"
            
        # 进度通知使用同步发送，确保重要的进度信息能到达
        success = await self._emit_event_sync(
            event_type="sync_progress", 
            level="info",
            message=message,
            details={
                "table": table_name,
                "records_synced": records_synced,
                "latest_time": latest_time,
                "is_progress_update": True
            },
            metrics={
                "records_synced": records_synced,
                "progress_timestamp": time.time()
            }
        )
        
        if not success:
            self.logger.warning(f"同步进度事件发送失败: {table_name} - {records_synced:,} 条记录")
    
    async def cleanup_success(self, records_deleted: int, duration: float):
        """清理成功事件"""
        await self.emit_event(
            event_type="cleanup_success",
            level="info",
            message=f"数据清理完成，删除 {records_deleted} 条记录",
            details={"records_deleted": records_deleted},
            metrics={
                "records_deleted": records_deleted,
                "duration": duration
            }
        )
    
    async def cleanup_failure(self, error: str):
        """清理失败事件"""
        await self.emit_event(
            event_type="cleanup_failure",
            level="error",
            message=f"数据清理失败: {error}",
            details={"error": error}
        )
    
    async def migration_success(self, migration_type: str, records_migrated: int, duration: float):
        """迁移成功事件"""
        await self.emit_event(
            event_type="migration_success", 
            level="info",
            message=f"{migration_type}迁移完成，处理 {records_migrated} 条记录",
            details={
                "migration_type": migration_type,
                "records_migrated": records_migrated
            },
            metrics={
                "records_migrated": records_migrated,
                "duration": duration
            }
        )
    
    async def migration_failure(self, migration_type: str, error: str):
        """迁移失败事件"""
        await self.emit_event(
            event_type="migration_failure",
            level="error",
            message=f"{migration_type}迁移失败: {error}",
            details={
                "migration_type": migration_type,
                "error": error
            }
        )
    
    async def health_check_failed(self, component: str, error: str):
        """健康检查失败事件"""
        await self.emit_event(
            event_type="health_check_failure",
            level="warning",
            message=f"{component}健康检查失败: {error}",
            details={
                "component": component,
                "error": error
            }
        )
    
    async def performance_warning(self, metric_name: str, current_value: float, threshold: float):
        """性能警告事件"""
        await self.emit_event(
            event_type="performance_warning",
            level="warning",
            message=f"{metric_name}性能指标超过阈值: {current_value} > {threshold}",
            details={
                "metric_name": metric_name,
                "current_value": current_value,
                "threshold": threshold
            },
            metrics={
                metric_name: current_value,
                f"{metric_name}_threshold": threshold
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        return self.stats.copy()
    
    async def test_connection(self) -> bool:
        """测试与监控服务的连接"""
        try:
            url = f"{self.monitor_url}/health"
            timeout = aiohttp.ClientTimeout(total=3)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        self.logger.info("监控服务连接正常")
                        return True
                    else:
                        self.logger.warning(f"监控服务返回状态: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.warning(f"监控服务连接测试失败: {e}")
            return False


# 全局客户端实例
_monitor_client = None


def get_monitor_client() -> DataSyncMonitorClient:
    """获取全局监控客户端实例"""
    global _monitor_client
    if _monitor_client is None:
        _monitor_client = DataSyncMonitorClient()
    return _monitor_client


def setup_monitor_client(service_name: str = "datasync", monitor_url: str = "http://localhost:9527") -> DataSyncMonitorClient:
    """
    设置监控客户端
    
    Args:
        service_name: 服务名称
        monitor_url: 监控服务URL
        
    Returns:
        配置好的监控客户端实例
    """
    global _monitor_client
    _monitor_client = DataSyncMonitorClient(service_name, monitor_url)
    return _monitor_client