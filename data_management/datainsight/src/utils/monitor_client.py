#!/usr/bin/env python3
"""
DataInsight监控客户端
基于DataSync监控客户端架构，专门为DataInsight服务定制
"""

import asyncio
import aiohttp
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class DataInsightMonitorClient:
    """DataInsight监控客户端"""
    
    def __init__(self, service_name: str = "datainsight", monitor_url: str = "http://localhost:9527"):
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
            event_type: 事件类型 (如: indicator_calculation_success, indicator_calculation_failure等)
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
            "timestamp": datetime.now(timezone.utc).isoformat()
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
                    self.stats['last_success'] = datetime.now(timezone.utc).isoformat()
                    if attempt > 0:
                        self.logger.info(f"事件发送成功 (重试 {attempt} 次): {payload['event_type']}")
                    return
                    
            except Exception as e:
                self.logger.warning(f"事件发送尝试 {attempt + 1} 失败: {e}")
                if attempt < self.retry_count:
                    await asyncio.sleep(1 * (attempt + 1))  # 递增延迟
        
        # 所有尝试都失败了
        self.stats['events_failed'] += 1
        self.stats['last_failure'] = datetime.now(timezone.utc).isoformat()
        self.logger.error(f"事件发送最终失败: {payload['event_type']} - {payload['message']}")
    
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
    
    # DataInsight专用监控事件方法
    
    async def emit_calculation_success(self, count: int, duration: float, calc_time: datetime):
        """指标计算成功事件"""
        await self.emit_event(
            event_type="indicator_calculation_success",
            level="info",
            message=f"指标计算成功，完成 {count} 个指标计算",
            details={
                "indicators_calculated": count,
                "calculation_time": calc_time.isoformat(),
                "duration_seconds": duration
            },
            metrics={
                "indicators_count": count,
                "duration": duration,
                "throughput": count / max(duration, 1)
            }
        )
    
    async def emit_timepoint_completion(self, time_str: str, count: int, duration: float, calc_time: datetime):
        """时间点指标计算完成事件"""
        await self.emit_event(
            event_type="timepoint_completion",
            level="info",
            message=f"✅ 已完成 {time_str} 时间点的指标计算，共{count}个指标，耗时{duration:.1f}秒",
            details={
                "timepoint": time_str,
                "indicators_calculated": count,
                "calculation_time": calc_time.isoformat(),
                "duration_seconds": duration
            },
            metrics={
                "indicators_count": count,
                "duration": duration,
                "throughput": count / max(duration, 1)
            }
        )
    
    async def emit_calculation_failure(self, failed_indicators: List[str], duration: float, calc_time: datetime):
        """指标计算失败事件"""
        await self.emit_event(
            event_type="indicator_calculation_failure",
            level="error",
            message=f"指标计算失败，失败指标: {', '.join(failed_indicators)}",
            details={
                "failed_indicators": failed_indicators,
                "failure_count": len(failed_indicators),
                "calculation_time": calc_time.isoformat(),
                "duration_seconds": duration
            },
            metrics={
                "failed_count": len(failed_indicators),
                "duration": duration
            }
        )
    
    async def emit_execution_error(self, error: str):
        """执行错误事件"""
        await self.emit_event(
            event_type="execution_error",
            level="error",
            message=f"DataInsight执行异常: {error}",
            details={
                "error": error,
                "component": "scheduler"
            }
        )
    
    async def emit_integrity_success(self, gap_hours: float):
        """数据完整性检查成功事件"""
        await self.emit_event(
            event_type="integrity_check_success",
            level="info",
            message=f"数据完整性检查通过，数据缺口 {gap_hours:.1f} 小时",
            details={
                "gap_hours": gap_hours,
                "status": "healthy"
            },
            metrics={
                "data_gap_hours": gap_hours
            }
        )
    
    async def emit_integrity_failure(self, error: str, gap_hours: float):
        """数据完整性检查失败事件"""
        await self.emit_event(
            event_type="integrity_check_failure",
            level="error",
            message=f"数据完整性检查失败: {error}",
            details={
                "error": error,
                "gap_hours": gap_hours,
                "status": "unhealthy"
            },
            metrics={
                "data_gap_hours": gap_hours
            }
        )
    
    async def emit_backfill_progress(self, batch_count: int, current_time: str):
        """补算进度事件"""
        await self.emit_event(
            event_type="backfill_progress",
            level="info",
            message=f"数据补算进度更新: 已完成 {batch_count} 个批次",
            details={
                "batches_completed": batch_count,
                "current_time": current_time,
                "operation": "backfill"
            },
            metrics={
                "batches_completed": batch_count,
                "progress_timestamp": time.time()
            }
        )
    
    async def emit_trigger_file_processing(self, filename: str, action: str, success: bool):
        """触发文件处理事件"""
        level = "info" if success else "warning"
        await self.emit_event(
            event_type="trigger_file_processing",
            level=level,
            message=f"触发文件 {action}: {filename}",
            details={
                "filename": filename,
                "action": action,
                "success": success
            }
        )
    
    async def emit_critical_failure(self, indicator_name: str, consecutive_failures: int):
        """连续失败达到阈值的严重事件"""
        await self.emit_event(
            event_type="critical_failure",
            level="critical",
            message=f"指标 {indicator_name} 连续失败 {consecutive_failures} 次，需要立即检查",
            details={
                "indicator_name": indicator_name,
                "consecutive_failures": consecutive_failures,
                "severity": "critical"
            },
            metrics={
                "consecutive_failures": consecutive_failures
            }
        )
    
    async def emit_database_failure(self, operation: str, error: str):
        """数据库操作失败事件"""
        await self.emit_event(
            event_type="database_failure",
            level="error",
            message=f"数据库操作失败: {operation}",
            details={
                "operation": operation,
                "error": error,
                "component": "database"
            }
        )
    
    async def emit_daemon_status(self, status: str, message: str = ""):
        """守护进程状态事件"""
        level = "info" if status in ["starting", "running"] else "warning" if status == "stopping" else "error"
        await self.emit_event(
            event_type="daemon_status",
            level=level,
            message=f"DataInsight守护进程状态: {status} - {message}",
            details={
                "daemon_status": status,
                "message": message
            }
        )
    
    async def emit_performance_warning(self, metric_name: str, current_value: float, threshold: float):
        """性能警告事件"""
        await self.emit_event(
            event_type="performance_warning",
            level="warning",
            message=f"性能指标超过阈值: {metric_name} = {current_value} > {threshold}",
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
    
    async def emit_indicator_dependency_failure(self, indicator_name: str, missing_dependencies: List[str]):
        """指标依赖检查失败事件"""
        await self.emit_event(
            event_type="dependency_check_failure",
            level="warning",
            message=f"指标 {indicator_name} 依赖检查失败，缺少依赖: {', '.join(missing_dependencies)}",
            details={
                "indicator_name": indicator_name,
                "missing_dependencies": missing_dependencies,
                "action": "skipped"
            }
        )
    
    async def emit_batch_completion(self, start_time: str, end_time: str, processed_count: int, duration: float):
        """批量处理完成事件"""
        await self.emit_event(
            event_type="batch_completion",
            level="info",
            message=f"批量处理完成: {start_time} 到 {end_time}，处理 {processed_count} 个时间点",
            details={
                "start_time": start_time,
                "end_time": end_time,
                "processed_count": processed_count,
                "duration_seconds": duration
            },
            metrics={
                "processed_count": processed_count,
                "duration": duration,
                "processing_rate": processed_count / max(duration, 1)
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


def get_monitor_client() -> DataInsightMonitorClient:
    """获取全局监控客户端实例"""
    global _monitor_client
    if _monitor_client is None:
        _monitor_client = DataInsightMonitorClient()
    return _monitor_client


def setup_monitor_client(service_name: str = "datainsight", monitor_url: str = "http://localhost:9527") -> DataInsightMonitorClient:
    """
    设置监控客户端
    
    Args:
        service_name: 服务名称
        monitor_url: 监控服务URL
        
    Returns:
        配置好的监控客户端实例
    """
    global _monitor_client
    _monitor_client = DataInsightMonitorClient(service_name, monitor_url)
    return _monitor_client


class MonitoringMixin:
    """监控功能混入类，为其他类提供监控能力"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_client = get_monitor_client()
    
    async def log_and_monitor_success(self, operation: str, details: Dict[str, Any] = None, metrics: Dict[str, Any] = None):
        """记录并监控成功事件"""
        if hasattr(self, 'logger'):
            self.logger.info(f"✅ {operation} 成功")
        
        await self.monitor_client.emit_event(
            event_type=f"{operation.lower().replace(' ', '_')}_success",
            level="info",
            message=f"{operation} 执行成功",
            details=details,
            metrics=metrics
        )
    
    async def log_and_monitor_failure(self, operation: str, error: str, details: Dict[str, Any] = None):
        """记录并监控失败事件"""
        if hasattr(self, 'logger'):
            self.logger.error(f"❌ {operation} 失败: {error}")
        
        await self.monitor_client.emit_event(
            event_type=f"{operation.lower().replace(' ', '_')}_failure",
            level="error",
            message=f"{operation} 执行失败: {error}",
            details={**(details or {}), "error": error}
        )


def monitor_async_operation(operation_name: str):
    """异步操作监控装饰器"""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = await func(self, *args, **kwargs)
                duration = time.time() - start_time
                
                if hasattr(self, 'monitor_client'):
                    await self.monitor_client.emit_event(
                        event_type=f"{operation_name}_success",
                        level="info",
                        message=f"{operation_name} 操作成功",
                        metrics={"duration": duration}
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                if hasattr(self, 'monitor_client'):
                    await self.monitor_client.emit_event(
                        event_type=f"{operation_name}_failure", 
                        level="error",
                        message=f"{operation_name} 操作失败: {str(e)}",
                        details={"error": str(e)},
                        metrics={"duration": duration}
                    )
                
                raise e
        return wrapper
    return decorator