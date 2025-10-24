#!/usr/bin/env python3
"""
DataInsight自定义异常类
提供更精确的错误分类和处理
"""


class DataInsightError(Exception):
    """DataInsight基础异常"""
    pass


class DatabaseConnectionError(DataInsightError):
    """数据库连接异常"""
    def __init__(self, message: str, connection_string: str = None):
        self.connection_string = connection_string
        super().__init__(message)


class DatabaseQueryError(DataInsightError):
    """数据库查询异常"""
    def __init__(self, message: str, query: str = None, error_code: str = None):
        self.query = query
        self.error_code = error_code
        super().__init__(message)


class DatabaseTimeoutError(DatabaseConnectionError):
    """数据库超时异常"""
    pass


class IndicatorCalculationError(DataInsightError):
    """指标计算异常"""
    def __init__(self, message: str, indicator_name: str = None, calc_time: str = None):
        self.indicator_name = indicator_name
        self.calc_time = calc_time
        super().__init__(message)


class DependencyCheckError(DataInsightError):
    """依赖检查异常"""
    def __init__(self, message: str, missing_dependencies: list = None):
        self.missing_dependencies = missing_dependencies or []
        super().__init__(message)


class DataIntegrityError(DataInsightError):
    """数据完整性异常"""
    def __init__(self, message: str, gap_hours: float = None):
        self.gap_hours = gap_hours
        super().__init__(message)


class ConfigurationError(DataInsightError):
    """配置异常"""
    def __init__(self, message: str, config_path: str = None):
        self.config_path = config_path
        super().__init__(message)


class MonitoringError(DataInsightError):
    """监控系统异常"""
    def __init__(self, message: str, monitor_url: str = None):
        self.monitor_url = monitor_url
        super().__init__(message)


class SchedulerError(DataInsightError):
    """调度器异常"""
    pass


class NotificationError(DataInsightError):
    """通知系统异常"""
    def __init__(self, message: str, notification_type: str = None):
        self.notification_type = notification_type
        super().__init__(message)