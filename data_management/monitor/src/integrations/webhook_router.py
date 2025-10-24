#!/usr/bin/env python3
"""
Webhook路由器
负责根据路由规则将事件发送到相应的webhook端点
"""

import asyncio
import aiohttp
import json
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.config_manager import ConfigManager


class WebhookRouter:
    """Webhook路由器"""
    
    def __init__(self, config_path: str = "/databao/monitor/config/webhooks.yml"):
        """初始化路由器"""
        self.logger = logging.getLogger('monitor.webhook')
        self.config_path = Path(config_path)
        self.config_manager = None
        
        # HTTP客户端配置
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.max_retries = 2
    
    async def load_config(self):
        """加载配置"""
        try:
            # 延迟导入ConfigManager避免循环依赖
            if not self.config_manager:
                self.config_manager = ConfigManager()
                await self.config_manager.load_configs()
            
            self.logger.info("Webhook路由配置加载完成")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
    
    async def send_event(self, event):
        """发送事件到所有匹配的webhook"""
        try:
            if not self.config_manager:
                await self.load_config()
            
            # 获取匹配的规则
            matching_rules = self.config_manager.get_matching_rules(event.to_dict())
            
            if not matching_rules:
                self.logger.warning(f"没有匹配的webhook规则: {event.event_type}")
                return
            
            # 并发发送到所有匹配的webhook
            tasks = []
            for rule in matching_rules:
                if rule.enabled:
                    task = asyncio.create_task(self._send_to_webhook(event, rule))
                    tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"发送事件失败: {e}")
    
    async def _send_to_webhook(self, event, rule):
        """发送到单个webhook"""
        try:
            if rule.webhook.type == "feishu":
                await self._send_feishu_message(event, rule)
            else:
                await self._send_generic_webhook(event, rule)
                
        except Exception as e:
            self.logger.error(f"Webhook发送失败 [{rule.name}]: {e}")
    
    async def _send_feishu_message(self, event, rule):
        """发送飞书消息"""
        try:
            # 创建飞书消息格式
            payload = self._create_feishu_payload(event, rule)
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(rule.webhook.url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('code') == 0:
                            self.logger.info(f"飞书消息发送成功 [{rule.name}]: {event.event_type}")
                        else:
                            self.logger.error(f"飞书消息发送失败 [{rule.name}]: {result}")
                    else:
                        self.logger.error(f"飞书消息HTTP错误 [{rule.name}]: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"发送飞书消息异常 [{rule.name}]: {e}")
    
    def _create_feishu_payload(self, event, rule):
        """创建飞书消息载荷"""
        # 根据事件级别确定颜色和图标
        level_config = {
            "info": ("blue", "✅"),
            "warning": ("yellow", "⚠️"),
            "error": ("red", "🚨"),
            "critical": ("red", "💥")
        }
        
        color, icon = level_config.get(event.level, ("blue", "ℹ️"))
        
        # 创建消息内容
        if rule.webhook.silent:
            # 静音模式：简化消息
            content = f"{icon} **{event.service}** {event.event_type}\n"
            content += f"**消息**: {event.message}\n"
            content += f"**时间**: {event.timestamp}"
            
            if event.metrics:
                content += "\n**指标**:\n"
                for key, value in event.metrics.items():
                    content += f"• {key}: {value}\n"
        else:
            # 详细诊断模式
            content = f"{icon} **{event.service.title()} {event.level.upper()}**\n\n"
            content += f"**事件**: {event.event_type}\n"
            content += f"**消息**: {event.message}\n"
            content += f"**时间**: {event.timestamp}\n"
            
            if event.details:
                content += "\n**详情**:\n"
                for key, value in event.details.items():
                    content += f"• **{key}**: {value}\n"
            
            if event.metrics:
                content += "\n**指标**:\n"
                for key, value in event.metrics.items():
                    content += f"• **{key}**: {value}\n"
        
        # 添加@用户
        if rule.webhook.at_users:
            mentions = []
            for user in rule.webhook.at_users:
                if user == "@all":
                    mentions.append("<at user_id=\"all\">所有人</at>")
                else:
                    mentions.append(f"<at user_id=\"{user}\">{user}</at>")
            
            if mentions:
                content = " ".join(mentions) + "\n\n" + content
        
        return {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True,
                    "enable_forward": True
                },
                "header": {
                    "title": {
                        "content": f"{icon} DataBao {event.service.title()} {event.level.upper()}",
                        "tag": "plain_text"
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "content": content,
                            "tag": "lark_md"
                        }
                    }
                ]
            }
        }
    
    async def _send_generic_webhook(self, event, rule):
        """发送通用webhook"""
        try:
            payload = {
                "event": event.to_dict(),
                "rule": rule.name,
                "timestamp": event.timestamp
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(rule.webhook.url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook发送成功 [{rule.name}]: {event.event_type}")
                    else:
                        self.logger.error(f"Webhook HTTP错误 [{rule.name}]: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"发送通用webhook异常 [{rule.name}]: {e}")
    
    async def health_check(self):
        """健康检查"""
        try:
            if not self.config_manager:
                await self.load_config()
            
            total_rules = len(self.config_manager.route_rules)
            enabled_rules = len([r for r in self.config_manager.route_rules if r.enabled])
            
            return {
                "status": "healthy",
                "total_rules": total_rules,
                "enabled_rules": enabled_rules
            }
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }


# 全局实例
_webhook_router = None

def get_webhook_router():
    """获取全局webhook路由器实例"""
    global _webhook_router
    if _webhook_router is None:
        _webhook_router = WebhookRouter()
    return _webhook_router