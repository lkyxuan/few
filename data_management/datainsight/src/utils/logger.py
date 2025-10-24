#!/usr/bin/env python3
"""
DataInsight日志工具
提供统一的日志配置和管理功能
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def setup_logger(
    name: str = 'datainsight',
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False
) -> logging.Logger:
    """
    设置DataInsight日志器
    
    Args:
        name: 日志器名称
        config: 日志配置字典
        verbose: 是否启用详细日志模式
        
    Returns:
        配置好的日志器
    """
    # 默认配置
    default_config = {
        'level': 'INFO',
        'file': '/var/log/databao/datainsight.log',
        'rotate_days': 30,
        'max_file_size': '50MB',
        'backup_count': 5,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'date_format': '%Y-%m-%d %H:%M:%S',
        'loggers': {
            'scheduler': 'INFO',
            'indicators': 'INFO', 
            'database': 'WARNING',
            'monitoring': 'INFO',
            'triggers': 'INFO'
        }
    }
    
    # 合并配置
    if config:
        log_config = {**default_config, **config}
    else:
        log_config = default_config
    
    # 调整日志级别
    if verbose:
        log_config['level'] = 'DEBUG'
        for logger_name in log_config['loggers']:
            log_config['loggers'][logger_name] = 'DEBUG'
    
    # 创建日志器
    logger = logging.getLogger(name)
    logger.setLevel(_get_log_level(log_config['level']))
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 创建格式化器
    formatter = logging.Formatter(
        log_config['format'],
        datefmt=log_config['date_format']
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_get_log_level(log_config['level']))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器
    try:
        # 确保日志目录存在
        log_file = Path(log_config['file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建轮转文件处理器
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_config['file'],
            when='midnight',
            interval=1,
            backupCount=log_config['rotate_days'],
            encoding='utf-8'
        )
        
        file_handler.setLevel(_get_log_level(log_config['level']))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 设置文件名后缀
        file_handler.suffix = "%Y%m%d"
        
    except Exception as e:
        logger.warning(f"无法创建日志文件处理器: {e}")
    
    # 设置子日志器
    for logger_name, level in log_config.get('loggers', {}).items():
        sub_logger = logging.getLogger(f'{name}.{logger_name}')
        sub_logger.setLevel(_get_log_level(level))
        # 子日志器继承父日志器的处理器
        sub_logger.propagate = True
    
    # 防止重复日志
    logger.propagate = False
    
    logger.info(f"日志系统初始化完成: {name}")
    return logger


def _get_log_level(level_str: str) -> int:
    """将字符串日志级别转换为数字"""
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return level_map.get(level_str.upper(), logging.INFO)


def _parse_size(size_str: str) -> int:
    """解析大小字符串为字节数"""
    size_str = size_str.upper()
    multipliers = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024
    }
    
    for suffix, multiplier in multipliers.items():
        if size_str.endswith(suffix):
            try:
                return int(size_str[:-len(suffix)]) * multiplier
            except ValueError:
                break
    
    # 默认为50MB
    return 50 * 1024 * 1024


class DataInsightLogger:
    """DataInsight专用日志工具类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DataInsight日志工具
        
        Args:
            config: 完整的配置字典
        """
        self.config = config
        self.log_config = config.get('logging', {})
        self._setup_main_logger()
        self._setup_component_loggers()
    
    def _setup_main_logger(self):
        """设置主日志器"""
        self.main_logger = setup_logger(
            'datainsight',
            self.log_config,
            verbose=self.config.get('debug', {}).get('verbose_logging', False)
        )
    
    def _setup_component_loggers(self):
        """设置组件日志器"""
        self.scheduler_logger = logging.getLogger('datainsight.scheduler')
        self.database_logger = logging.getLogger('datainsight.database')
        self.indicators_logger = logging.getLogger('datainsight.indicators')
        self.monitoring_logger = logging.getLogger('datainsight.monitoring')
        self.triggers_logger = logging.getLogger('datainsight.triggers')
    
    def get_logger(self, component: str = 'main') -> logging.Logger:
        """
        获取指定组件的日志器
        
        Args:
            component: 组件名称 ('main', 'scheduler', 'database', 'indicators', 'monitoring', 'triggers')
            
        Returns:
            对应的日志器
        """
        logger_map = {
            'main': self.main_logger,
            'scheduler': self.scheduler_logger,
            'database': self.database_logger,
            'indicators': self.indicators_logger,
            'monitoring': self.monitoring_logger,
            'triggers': self.triggers_logger
        }
        
        return logger_map.get(component, self.main_logger)
    
    def log_execution_start(self, indicator_name: str, priority: int, target_time: str):
        """记录指标执行开始"""
        self.indicators_logger.info(
            f"🚀 开始执行指标计算: 优先级{priority} - {indicator_name} - 时间{target_time}"
        )
    
    def log_execution_success(self, indicator_name: str, priority: int, duration: float, result_count: int):
        """记录指标执行成功"""
        self.indicators_logger.info(
            f"✅ 指标计算成功: 优先级{priority} - {indicator_name} - "
            f"耗时{duration:.2f}秒 - 结果{result_count}条"
        )
    
    def log_execution_failure(self, indicator_name: str, priority: int, error: str, duration: float = 0):
        """记录指标执行失败"""
        self.indicators_logger.error(
            f"❌ 指标计算失败: 优先级{priority} - {indicator_name} - "
            f"错误:{error} - 耗时{duration:.2f}秒"
        )
    
    def log_dependency_check(self, indicator_name: str, dependencies: list, result: bool):
        """记录依赖检查结果"""
        if result:
            self.scheduler_logger.debug(
                f"✅ 依赖检查通过: {indicator_name} - 依赖: {', '.join(dependencies)}"
            )
        else:
            self.scheduler_logger.warning(
                f"⚠️ 依赖检查失败: {indicator_name} - 依赖: {', '.join(dependencies)}"
            )
    
    def log_trigger_file_processing(self, filename: str, data_time: str, action: str = 'processing'):
        """记录触发文件处理"""
        action_emojis = {
            'discovered': '🔍',
            'processing': '⚙️',
            'completed': '✅',
            'failed': '❌',
            'deleted': '🗑️'
        }
        
        emoji = action_emojis.get(action, '📄')
        self.triggers_logger.info(f"{emoji} 触发文件{action}: {filename} - 数据时间: {data_time}")
    
    def log_database_operation(self, operation: str, table: str, result: str, duration: float = 0):
        """记录数据库操作"""
        self.database_logger.debug(
            f"🔗 数据库操作: {operation} - 表: {table} - 结果: {result} - 耗时{duration:.3f}秒"
        )
    
    def log_integrity_check(self, result: bool, message: str, gap_hours: float = 0):
        """记录数据完整性检查"""
        if result:
            self.scheduler_logger.info(f"✅ 数据完整性检查通过: {message} - 缺口{gap_hours:.1f}小时")
        else:
            self.scheduler_logger.warning(f"⚠️ 数据完整性检查失败: {message} - 缺口{gap_hours:.1f}小时")
    
    def log_backfill_progress(self, current_time: str, batch_count: int, total_estimate: int = 0):
        """记录补算进度"""
        if total_estimate > 0:
            progress = f"({batch_count}/{total_estimate})"
        else:
            progress = f"第{batch_count}批"
            
        self.scheduler_logger.info(f"📊 补算进度: {progress} - 当前时间: {current_time}")
    
    def log_monitoring_event(self, event_type: str, success: bool, message: str = ''):
        """记录监控事件发送"""
        if success:
            self.monitoring_logger.debug(f"📤 监控事件发送成功: {event_type} - {message}")
        else:
            self.monitoring_logger.warning(f"📤 监控事件发送失败: {event_type} - {message}")
    
    def log_config_loading(self, config_path: str, success: bool, indicators_count: int = 0):
        """记录配置加载"""
        if success:
            self.main_logger.info(f"⚙️ 配置加载成功: {config_path} - 指标数量: {indicators_count}")
        else:
            self.main_logger.error(f"⚙️ 配置加载失败: {config_path}")
    
    def log_daemon_status(self, status: str, message: str = ''):
        """记录守护进程状态"""
        status_emojis = {
            'starting': '🚀',
            'running': '🔄',
            'stopping': '⏹️',
            'stopped': '🛑',
            'error': '❌'
        }
        
        emoji = status_emojis.get(status, '📋')
        self.scheduler_logger.info(f"{emoji} 守护进程状态: {status} - {message}")
    
    def log_performance_metrics(self, metrics: Dict[str, float]):
        """记录性能指标"""
        metrics_str = ', '.join([f"{k}: {v:.3f}" for k, v in metrics.items()])
        self.main_logger.debug(f"📈 性能指标: {metrics_str}")
    
    def log_system_resource(self, cpu_percent: float, memory_mb: float, disk_usage: str = ''):
        """记录系统资源使用"""
        self.main_logger.debug(
            f"💻 系统资源: CPU {cpu_percent:.1f}%, 内存 {memory_mb:.1f}MB, 磁盘 {disk_usage}"
        )


def create_structured_log_entry(
    component: str,
    action: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    metrics: Optional[Dict[str, float]] = None
) -> str:
    """
    创建结构化日志条目
    
    Args:
        component: 组件名称
        action: 动作描述
        status: 状态 (success/failure/warning/info)
        details: 详细信息字典
        metrics: 指标数据字典
        
    Returns:
        格式化的日志消息
    """
    status_emojis = {
        'success': '✅',
        'failure': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'debug': '🔍'
    }
    
    emoji = status_emojis.get(status, '📋')
    message_parts = [f"{emoji} [{component}] {action}"]
    
    if details:
        detail_strs = [f"{k}={v}" for k, v in details.items()]
        message_parts.append(f"详情: {', '.join(detail_strs)}")
    
    if metrics:
        metric_strs = [f"{k}={v}" for k, v in metrics.items()]
        message_parts.append(f"指标: {', '.join(metric_strs)}")
    
    return ' | '.join(message_parts)


def log_exception(logger: logging.Logger, operation: str, exception: Exception):
    """
    记录异常信息
    
    Args:
        logger: 日志器
        operation: 操作描述
        exception: 异常对象
    """
    logger.error(f"❌ 操作异常: {operation}")
    logger.error(f"异常类型: {type(exception).__name__}")
    logger.error(f"异常消息: {str(exception)}")
    
    # 在调试模式下记录完整的堆栈跟踪
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("完整堆栈跟踪:", exc_info=True)


class PerformanceLogger:
    """性能监控日志器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        """开始计时"""
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """结束计时并记录"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type is None:
                self.logger.debug(f"⏱️ 操作完成，耗时: {duration:.3f}秒")
            else:
                self.logger.warning(f"⏱️ 操作异常结束，耗时: {duration:.3f}秒")


def performance_log(logger: logging.Logger):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                logger.debug(f"⏱️ {func.__name__} 执行完成，耗时: {duration:.3f}秒")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                logger.warning(f"⏱️ {func.__name__} 执行异常，耗时: {duration:.3f}秒")
                raise e
        return wrapper
    return decorator