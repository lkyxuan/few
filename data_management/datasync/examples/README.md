# DataSync 监控接口使用指南

## 概述

DataSync监控接口提供了标准化的事件发送机制，允许外部监控系统通过webhook接收DataSync的运行状态、事件通知和性能指标。

## 核心功能

- **事件发送**: 在关键操作时发送结构化事件
- **回调注册**: 支持注册多个回调函数处理事件
- **灵活配置**: 支持不同类型的webhook和通知方式
- **丰富指标**: 包含详细的性能和状态指标

## 事件类型

### 同步事件
- `SYNC_START`: 数据同步开始
- `SYNC_SUCCESS`: 数据同步成功
- `SYNC_FAILURE`: 数据同步失败

### 清理事件  
- `CLEANUP_START`: 远程数据清理开始
- `CLEANUP_SUCCESS`: 远程数据清理成功
- `CLEANUP_FAILURE`: 远程数据清理失败

### 迁移事件
- `MIGRATION_START`: 数据迁移开始
- `MIGRATION_SUCCESS`: 数据迁移成功
- `MIGRATION_FAILURE`: 数据迁移失败

### 系统事件
- `HEALTH_CHECK`: 健康检查结果
- `SERVICE_STATUS`: 服务状态更新
- `PERFORMANCE_WARNING`: 性能警告
- `STORAGE_WARNING`: 存储空间警告

## 事件级别

- `INFO`: 信息事件（正常操作）
- `WARNING`: 警告事件（需要关注）
- `ERROR`: 错误事件（操作失败）
- `CRITICAL`: 严重事件（系统问题）

## 使用方法

### 1. 基本使用

```python
from monitoring.monitor_interface import get_monitor_interface, EventType, EventLevel

# 获取全局监控接口
monitor = get_monitor_interface()

# 注册回调函数
def my_callback(event):
    print(f"收到事件: {event.event_type} - {event.message}")

monitor.register_callback(my_callback)

# 发送事件
monitor.emit_event(
    event_type=EventType.SYNC_SUCCESS,
    level=EventLevel.INFO,
    message="数据同步完成",
    details={"records_synced": 1000},
    metrics={"duration_seconds": 30}
)
```

### 2. Webhook集成

```python
import requests

def webhook_callback(event):
    """发送到外部webhook服务"""
    webhook_url = "https://your-webhook-url.com/hook"
    
    payload = {
        "service": "DataSync",
        "event_type": event.event_type,
        "level": event.level,
        "message": event.message,
        "timestamp": event.timestamp,
        "details": event.details,
        "metrics": event.metrics
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Webhook发送失败: {e}")

# 注册webhook回调
monitor.register_callback(webhook_callback)
```

### 3. 飞书机器人集成

```python
def feishu_bot_callback(event):
    """发送到飞书机器人"""
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_KEY"
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": f"DataSync通知\\n"
                   f"事件: {event.event_type}\\n"
                   f"级别: {event.level}\\n"
                   f"消息: {event.message}\\n"
                   f"时间: {event.timestamp}"
        }
    }
    
    requests.post(webhook_url, json=payload)
```

### 4. 获取状态信息

```python
# 获取综合状态
status = await monitor.get_comprehensive_status()
print(f"服务状态: {status['status']}")
print(f"同步指标: {status['sync_metrics']}")

# 获取同步指标
sync_metrics = await monitor.get_sync_metrics(hours=24)
print(f"24小时内同步成功次数: {sync_metrics['sync_success_count']}")

# 获取清理指标
cleanup_metrics = await monitor.get_cleanup_metrics(days=7)
print(f"7天内删除记录数: {cleanup_metrics['total_records_deleted']}")
```

## 配置示例

### 在守护进程中启用监控

```python
from monitoring.monitor_interface import setup_monitor_interface

# 设置监控接口（传入数据库管理器）
monitor = setup_monitor_interface(db_manager)

# 在管理器初始化时传入监控接口
sync_manager = SyncManager(config, monitor)
cleanup_manager = CleanupManager(config, monitor)  
migration_manager = MigrationManager(config, monitor)
```

### 配置多个通知方式

```python
# 同时配置多种通知方式
monitor.register_callback(console_callback)      # 控制台输出
monitor.register_callback(feishu_callback)       # 飞书通知
monitor.register_callback(email_callback)        # 邮件通知
monitor.register_callback(prometheus_callback)   # Prometheus指标
```

## 事件数据结构

每个监控事件包含以下字段：

```python
{
    "timestamp": "2025-08-29T10:30:00.000Z",  # 事件时间戳
    "event_type": "sync_success",              # 事件类型
    "level": "info",                           # 事件级别
    "service": "datasync",                     # 服务名称
    "message": "数据同步完成: 1000条记录",        # 事件消息
    "details": {                               # 详细信息
        "duration": 30.5,
        "tables": ["coin_data", "indicator_data"]
    },
    "metrics": {                               # 性能指标
        "records_synced": 1000,
        "duration_seconds": 30.5,
        "success_rate": 1.0
    }
}
```

## 示例文件

- `monitor_webhook_example.py`: 完整的webhook集成示例
- 包含Slack、飞书、控制台等多种通知方式

## 最佳实践

1. **事件过滤**: 只注册你关心的事件类型
2. **异步处理**: webhook回调应该是轻量级的，避免阻塞
3. **错误处理**: 回调函数中要处理网络异常
4. **批量发送**: 对于高频事件考虑批量发送
5. **监控回调**: 监控webhook本身的可用性

## 故障排查

### 事件没有发送
- 检查是否正确注册了回调函数
- 确认事件类型和级别匹配

### Webhook失败
- 检查网络连接和URL正确性
- 查看回调函数中的异常日志
- 确认webhook服务端可用性

### 性能问题
- 避免在回调中执行耗时操作
- 考虑使用队列异步处理事件
- 监控回调函数的执行时间