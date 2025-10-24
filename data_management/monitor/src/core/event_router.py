#!/usr/bin/env python3
"""
监控事件路由器
根据配置规则将接收到的事件路由到相应的webhook和通知渠道
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

from integrations.webhook_router import WebhookRouter
from integrations.diagnostic_formatter import DiagnosticFormatter


@dataclass
class MonitorEvent:
    """监控事件数据结构"""
    timestamp: str
    service: str
    event_type: str
    level: str
    message: str
    details: Dict[str, Any] = None
    metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.metrics is None:
            self.metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'service': self.service,
            'event_type': self.event_type,
            'level': self.level,
            'message': self.message,
            'details': self.details,
            'metrics': self.metrics
        }


class EventRouter:
    """事件路由器"""
    
    def __init__(self, webhook_router: WebhookRouter):
        """
        初始化事件路由器
        
        Args:
            webhook_router: Webhook路由器实例
        """
        self.webhook_router = webhook_router
        self.diagnostic_formatter = DiagnosticFormatter()
        self.logger = logging.getLogger('monitor.event_router')
        
        # 事件统计
        self.event_stats = {
            'total_events': 0,
            'events_by_service': {},
            'events_by_level': {},
            'events_by_type': {},
            'webhook_send_success': 0,
            'webhook_send_failure': 0
        }
        
        # 事件缓存（用于管理界面显示）
        self.recent_events: List[MonitorEvent] = []
        self.max_cache_size = 1000
    
    async def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理监控事件
        
        Args:
            event_data: 事件数据字典
            
        Returns:
            处理结果
        """
        try:
            # 创建事件对象
            event = MonitorEvent(
                timestamp=event_data.get('timestamp', datetime.utcnow().isoformat()),
                service=event_data.get('service', 'unknown'),
                event_type=event_data.get('event_type', 'unknown'),
                level=event_data.get('level', 'info'),
                message=event_data.get('message', ''),
                details=event_data.get('details', {}),
                metrics=event_data.get('metrics', {})
            )
            
            self.logger.info(f"处理事件: {event.service}.{event.event_type} [{event.level}] - {event.message}")
            
            # 更新统计
            self._update_stats(event)
            
            # 添加到缓存
            self._add_to_cache(event)
            
            # 获取匹配的路由规则
            matching_rules = self.webhook_router.config_manager.get_matching_rules(event.to_dict())
            
            if not matching_rules:
                self.logger.warning(f"没有匹配的路由规则: {event.service}.{event.event_type}")
                return {
                    'success': True,
                    'message': 'Event received but no matching rules',
                    'routes_matched': 0
                }
            
            # 直接使用webhook_router发送
            await self.webhook_router.send_event(event)
            results = [{"rule_name": "webhook_router", "success": True}]
            self.event_stats['webhook_send_success'] += 1
            
            return {
                'success': True,
                'message': f'Event processed with {len(results)} routes',
                'routes_matched': len(matching_rules),
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"事件处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _send_to_webhook(self, event: MonitorEvent, rule) -> Dict[str, Any]:
        """
        发送事件到webhook
        
        Args:
            event: 监控事件
            rule: 路由规则
            
        Returns:
            发送结果
        """
        try:
            # 格式化诊断消息（用于AI分析）
            diagnostic_message = self.diagnostic_formatter.format_diagnostic_message(event)
            
            # 准备webhook载荷
            if rule.webhook.type == 'feishu':
                payload = self.diagnostic_formatter.format_feishu_diagnostic(event)
                
                # 添加额外配置
                if rule.webhook.silent:
                    # 静音模式：简化消息格式
                    payload = self._create_simple_feishu_payload(event)
                    
                if rule.webhook.at_users:
                    # 添加@用户
                    content = payload['card']['elements'][0]['text']['content']
                    mentions = ' '.join([f"<at user_id=\"{user}\">{user}</at>" for user in rule.webhook.at_users])
                    payload['card']['elements'][0]['text']['content'] = f"{mentions}\n\n{content}"
                
                # 发送到飞书
                result = await self.webhook_router._send_feishu_message(rule.webhook.url, payload)
                
            else:
                # 其他类型的webhook（简化处理）
                payload = {
                    'event': event.to_dict(),
                    'diagnostic_message': diagnostic_message
                }
                result = await self.webhook_router._send_generic_webhook(rule.webhook.url, payload)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Webhook发送失败 [{rule.name}]: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_simple_feishu_payload(self, event: MonitorEvent) -> Dict[str, Any]:
        """创建简化的飞书消息载荷（用于静音模式）"""
        status_icons = {
            'info': '✅',
            'warning': '⚠️', 
            'error': '❌',
            'critical': '🚨'
        }
        
        icon = status_icons.get(event.level, 'ℹ️')
        
        # 简化消息内容
        simple_message = f"{icon} **{event.service}** {event.event_type}\n"
        simple_message += f"**消息**: {event.message}\n"
        simple_message += f"**时间**: {event.timestamp}"
        
        if event.metrics:
            simple_message += "\n**指标**:\n"
            for key, value in event.metrics.items():
                simple_message += f"• {key}: {value}\n"
        
        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": False,
                    "enable_forward": True
                },
                "header": {
                    "title": {
                        "content": f"{icon} {event.service.title()} {event.level.upper()}",
                        "tag": "plain_text"
                    },
                    "template": "blue" if event.level == 'info' else "yellow" if event.level == 'warning' else "red"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": simple_message,
                            "tag": "lark_md"
                        }
                    }
                ]
            }
        }
    
    def _update_stats(self, event: MonitorEvent):
        """更新事件统计"""
        self.event_stats['total_events'] += 1
        
        # 按服务统计
        service = event.service
        if service not in self.event_stats['events_by_service']:
            self.event_stats['events_by_service'][service] = 0
        self.event_stats['events_by_service'][service] += 1
        
        # 按级别统计
        level = event.level
        if level not in self.event_stats['events_by_level']:
            self.event_stats['events_by_level'][level] = 0
        self.event_stats['events_by_level'][level] += 1
        
        # 按类型统计
        event_type = event.event_type
        if event_type not in self.event_stats['events_by_type']:
            self.event_stats['events_by_type'][event_type] = 0
        self.event_stats['events_by_type'][event_type] += 1
    
    def _add_to_cache(self, event: MonitorEvent):
        """添加事件到缓存"""
        self.recent_events.append(event)
        
        # 保持缓存大小限制
        if len(self.recent_events) > self.max_cache_size:
            self.recent_events = self.recent_events[-self.max_cache_size:]
    
    def get_recent_events(self, limit: int = 50, service: str = None, level: str = None) -> List[Dict[str, Any]]:
        """
        获取最近的事件
        
        Args:
            limit: 返回事件数量限制
            service: 过滤服务名
            level: 过滤事件级别
            
        Returns:
            事件列表
        """
        events = self.recent_events.copy()
        
        # 过滤条件
        if service:
            events = [e for e in events if e.service == service]
        
        if level:
            events = [e for e in events if e.level == level]
        
        # 按时间倒序排列，取最新的
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return [e.to_dict() for e in events[:limit]]
    
    def get_event_stats(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        return self.event_stats.copy()
    
    async def send_test_event(self, service: str = "monitor", message: str = "测试事件") -> Dict[str, Any]:
        """
        发送测试事件
        
        Args:
            service: 服务名
            message: 测试消息
            
        Returns:
            处理结果
        """
        test_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': service,
            'event_type': 'test_event',
            'level': 'info',
            'message': message,
            'details': {'source': 'monitor_test'},
            'metrics': {'test_metric': 1}
        }
        
        return await self.process_event(test_event)