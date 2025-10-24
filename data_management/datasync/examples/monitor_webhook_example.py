#!/usr/bin/env python3
"""
DataSync 监控接口webhook示例
展示如何配置和使用监控接口来接收DataSync事件
"""

import asyncio
import json
import requests
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from monitoring.monitor_interface import DataSyncMonitorInterface, MonitorEvent, EventType, EventLevel


def webhook_callback(event: MonitorEvent):
    """
    Webhook回调函数示例
    将监控事件发送到外部webhook服务
    
    Args:
        event: 监控事件对象
    """
    # 配置你的webhook URL
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
    # 创建webhook载荷
    webhook_payload = {
        "text": f"DataSync事件通知",
        "attachments": [
            {
                "color": _get_color_by_level(event.level),
                "fields": [
                    {
                        "title": "事件类型",
                        "value": event.event_type,
                        "short": True
                    },
                    {
                        "title": "级别", 
                        "value": event.level,
                        "short": True
                    },
                    {
                        "title": "消息",
                        "value": event.message,
                        "short": False
                    },
                    {
                        "title": "时间",
                        "value": event.timestamp,
                        "short": True
                    }
                ]
            }
        ]
    }
    
    # 添加详细信息
    if event.details:
        webhook_payload["attachments"][0]["fields"].append({
            "title": "详细信息",
            "value": f"```{json.dumps(event.details, indent=2, ensure_ascii=False)}```",
            "short": False
        })
    
    # 添加指标信息
    if event.metrics:
        webhook_payload["attachments"][0]["fields"].append({
            "title": "指标",
            "value": f"```{json.dumps(event.metrics, indent=2, ensure_ascii=False)}```",
            "short": False
        })
    
    try:
        # 发送webhook请求
        response = requests.post(webhook_url, json=webhook_payload, timeout=5)
        response.raise_for_status()
        print(f"事件已发送到webhook: {event.event_type}")
        
    except Exception as e:
        print(f"发送webhook失败: {e}")


def console_callback(event: MonitorEvent):
    """
    控制台输出回调函数示例
    
    Args:
        event: 监控事件对象
    """
    print("=" * 60)
    print(f"📊 DataSync监控事件")
    print(f"类型: {event.event_type}")
    print(f"级别: {event.level}")
    print(f"时间: {event.timestamp}")
    print(f"消息: {event.message}")
    
    if event.details:
        print(f"详细信息:")
        for key, value in event.details.items():
            print(f"  {key}: {value}")
    
    if event.metrics:
        print(f"指标:")
        for key, value in event.metrics.items():
            print(f"  {key}: {value}")
    
    print("=" * 60)


def feishu_webhook_callback(event: MonitorEvent):
    """
    飞书webhook回调函数示例
    
    Args:
        event: 监控事件对象
    """
    feishu_webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_KEY"
    
    # 构造飞书消息卡片
    card_payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True,
                "enable_forward": True
            },
            "header": {
                "title": {
                    "content": f"DataSync {_translate_event_type(event.event_type)}",
                    "tag": "plain_text"
                },
                "template": _get_feishu_template_by_level(event.level)
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": event.message,
                        "tag": "plain_text"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**事件类型**: {event.event_type}",
                                "tag": "lark_md"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "content": f"**级别**: {event.level}",
                                "tag": "lark_md"
                            }
                        },
                        {
                            "is_short": False,
                            "text": {
                                "content": f"**时间**: {event.timestamp}",
                                "tag": "lark_md"
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    # 添加指标信息（如果存在）
    if event.metrics:
        metrics_text = "\n".join([f"• {k}: {v}" for k, v in event.metrics.items()])
        card_payload["card"]["elements"].append({
            "tag": "div",
            "text": {
                "content": f"**指标信息**:\n{metrics_text}",
                "tag": "lark_md"
            }
        })
    
    try:
        response = requests.post(feishu_webhook_url, json=card_payload, timeout=5)
        response.raise_for_status()
        print(f"事件已发送到飞书: {event.event_type}")
        
    except Exception as e:
        print(f"发送飞书消息失败: {e}")


def _get_color_by_level(level: str) -> str:
    """根据事件级别获取颜色"""
    colors = {
        "info": "good",
        "warning": "warning", 
        "error": "danger",
        "critical": "danger"
    }
    return colors.get(level, "good")


def _get_feishu_template_by_level(level: str) -> str:
    """根据事件级别获取飞书模板颜色"""
    templates = {
        "info": "blue",
        "warning": "yellow",
        "error": "red", 
        "critical": "red"
    }
    return templates.get(level, "blue")


def _translate_event_type(event_type: str) -> str:
    """翻译事件类型为中文"""
    translations = {
        "sync_start": "同步开始",
        "sync_success": "同步成功", 
        "sync_failure": "同步失败",
        "cleanup_start": "清理开始",
        "cleanup_success": "清理成功",
        "cleanup_failure": "清理失败",
        "migration_start": "迁移开始",
        "migration_success": "迁移成功",
        "migration_failure": "迁移失败",
        "health_check": "健康检查",
        "service_status": "服务状态"
    }
    return translations.get(event_type, event_type)


async def main():
    """主函数 - 展示监控接口使用"""
    print("DataSync监控接口示例")
    print("=" * 50)
    
    # 创建监控接口实例
    monitor = DataSyncMonitorInterface()
    
    # 注册不同类型的回调函数
    monitor.register_callback(console_callback)
    # monitor.register_callback(webhook_callback)  # 取消注释以启用webhook
    # monitor.register_callback(feishu_webhook_callback)  # 取消注释以启用飞书webhook
    
    # 发送一些示例事件
    print("发送示例监控事件...")
    
    # 同步开始事件
    monitor.emit_event(
        event_type=EventType.SYNC_START,
        level=EventLevel.INFO,
        message="开始数据同步",
        details={"dry_run": False, "tables": ["coin_data", "indicator_data"]}
    )
    
    await asyncio.sleep(1)
    
    # 同步成功事件
    monitor.emit_event(
        event_type=EventType.SYNC_SUCCESS,
        level=EventLevel.INFO,
        message="数据同步完成: 1250条记录",
        details={"duration": 45.2, "tasks_completed": 2},
        metrics={"records_synced": 1250, "duration_seconds": 45.2, "tasks_count": 2}
    )
    
    await asyncio.sleep(1)
    
    # 清理成功事件
    monitor.emit_event(
        event_type=EventType.CLEANUP_SUCCESS,
        level=EventLevel.INFO,
        message="远程数据清理完成: 5000条记录",
        details={"duration": 120.5, "retention_days": 60},
        metrics={"records_deleted": 5000, "duration_seconds": 120.5}
    )
    
    await asyncio.sleep(1)
    
    # 性能警告事件
    monitor.emit_event(
        event_type=EventType.PERFORMANCE_WARNING,
        level=EventLevel.WARNING,
        message="同步耗时超过阈值",
        details={"threshold_seconds": 300, "actual_seconds": 450},
        metrics={"sync_duration": 450, "threshold": 300}
    )
    
    await asyncio.sleep(1)
    
    # 错误事件示例
    monitor.emit_event(
        event_type=EventType.SYNC_FAILURE,
        level=EventLevel.ERROR,
        message="数据同步失败: 数据库连接超时",
        details={"error": "Connection timeout", "retry_count": 3},
        metrics={"duration_seconds": 30}
    )
    
    print("\n示例完成！")
    print("\n如何使用：")
    print("1. 取消注释webhook_callback或feishu_webhook_callback")
    print("2. 配置正确的webhook URL")
    print("3. 在你的DataSync服务中注册这些回调函数")
    print("4. DataSync将自动发送事件到配置的webhook")


if __name__ == "__main__":
    asyncio.run(main())