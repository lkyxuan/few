#!/usr/bin/env python3
"""
监控服务配置管理器
负责加载和管理监控服务的配置，包括webhook路由规则
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class WebhookConfig:
    """Webhook配置"""
    type: str  # feishu, slack, email, etc.
    url: str
    silent: bool = False
    at_users: List[str] = None
    
    def __post_init__(self):
        if self.at_users is None:
            self.at_users = []


@dataclass 
class RouteCondition:
    """路由条件"""
    service: Optional[str] = None
    event_types: List[str] = None
    levels: List[str] = None
    
    def __post_init__(self):
        if self.event_types is None:
            self.event_types = []
        if self.levels is None:
            self.levels = []
    
    def matches(self, event: Dict[str, Any]) -> bool:
        """检查事件是否匹配此条件"""
        import logging
        logger = logging.getLogger('monitor.config.debug')
        
        logger.info(f"=== 匹配调试 ===")
        logger.info(f"规则条件: service={self.service}, event_types={self.event_types}, levels={self.levels}")
        logger.info(f"事件数据: service={event.get('service')}, event_type={event.get('event_type')}, level={event.get('level')}")
        
        # 检查服务名
        if self.service and event.get('service') != self.service:
            logger.info(f"服务名不匹配: {event.get('service')} != {self.service}")
            return False
            
        # 检查事件类型
        if self.event_types and event.get('event_type') not in self.event_types:
            logger.info(f"事件类型不匹配: {event.get('event_type')} not in {self.event_types}")
            return False
            
        # 检查事件级别
        if self.levels and event.get('level') not in self.levels:
            logger.info(f"事件级别不匹配: {event.get('level')} not in {self.levels}")
            return False
        
        logger.info("条件匹配成功!")
        return True


@dataclass
class RouteRule:
    """路由规则"""
    name: str
    conditions: RouteCondition
    webhook: WebhookConfig
    additional_channels: List[Dict[str, Any]] = None
    enabled: bool = True
    
    def __post_init__(self):
        if self.additional_channels is None:
            self.additional_channels = []


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "/databao/monitor/config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger('monitor.config')
        
        # 配置数据
        self.server_config = {}
        self.route_rules: List[RouteRule] = []
        self.general_config = {}
        
        # 配置文件路径
        self.monitor_config_path = self.config_dir / "monitor.yml"
        self.webhooks_config_path = self.config_dir / "webhooks.yml"
    
    async def load_configs(self):
        """加载所有配置文件"""
        try:
            # 确保配置目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # 加载基础配置
            await self._load_monitor_config()
            
            # 加载webhook配置
            await self._load_webhook_config()
            
            self.logger.info(f"配置加载完成: {len(self.route_rules)}个路由规则")
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            raise
    
    async def _load_monitor_config(self):
        """加载监控服务基础配置"""
        if self.monitor_config_path.exists():
            try:
                with open(self.monitor_config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                    
                self.server_config = config_data.get('server', {})
                self.general_config = config_data.get('general', {})
                
                self.logger.info(f"加载监控配置: {self.monitor_config_path}")
                
            except Exception as e:
                self.logger.error(f"加载监控配置失败: {e}")
                # 使用默认配置
                self._create_default_monitor_config()
        else:
            # 创建默认配置文件
            self._create_default_monitor_config()
    
    async def _load_webhook_config(self):
        """加载webhook路由配置"""
        if self.webhooks_config_path.exists():
            try:
                with open(self.webhooks_config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                # 解析路由规则
                self.route_rules = []
                for rule_data in config_data.get('routing_rules', []):
                    rule = self._parse_route_rule(rule_data)
                    if rule:
                        self.route_rules.append(rule)
                
                self.logger.info(f"加载webhook配置: {len(self.route_rules)}个规则")
                
            except Exception as e:
                self.logger.error(f"加载webhook配置失败: {e}")
                # 创建默认配置
                self._create_default_webhook_config()
        else:
            # 创建默认配置文件
            self._create_default_webhook_config()
    
    def _parse_route_rule(self, rule_data: Dict[str, Any]) -> Optional[RouteRule]:
        """解析路由规则"""
        try:
            # 解析条件
            conditions_data = rule_data.get('conditions', {})
            conditions = RouteCondition(
                service=conditions_data.get('service'),
                event_types=conditions_data.get('event_types', []),
                levels=conditions_data.get('levels', [])
            )
            
            # 解析webhook配置
            webhook_data = rule_data.get('webhook', {})
            webhook = WebhookConfig(
                type=webhook_data.get('type', 'feishu'),
                url=webhook_data.get('url', ''),
                silent=webhook_data.get('silent', False),
                at_users=webhook_data.get('at_users', [])
            )
            
            # 创建规则
            rule = RouteRule(
                name=rule_data.get('name', ''),
                conditions=conditions,
                webhook=webhook,
                additional_channels=rule_data.get('additional_channels', []),
                enabled=rule_data.get('enabled', True)
            )
            
            return rule
            
        except Exception as e:
            self.logger.error(f"解析路由规则失败: {rule_data.get('name', 'unknown')} - {e}")
            return None
    
    def _create_default_monitor_config(self):
        """创建默认监控配置"""
        default_config = {
            'server': {
                'host': '0.0.0.0',
                'port': 9527,
                'workers': 4
            },
            'storage': {
                'metrics_retention_hours': 168,
                'events_retention_days': 30
            },
            'logging': {
                'level': 'INFO',
                'file': '/var/log/databao/monitor.log',
                'max_size': '100MB',
                'backup_count': 5
            }
        }
        
        self.server_config = default_config['server']
        self.general_config = {
            'storage': default_config['storage'],
            'logging': default_config['logging']
        }
        
        # 保存默认配置文件
        try:
            with open(self.monitor_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"创建默认监控配置: {self.monitor_config_path}")
        except Exception as e:
            self.logger.error(f"创建默认配置失败: {e}")
    
    def _create_default_webhook_config(self):
        """创建默认webhook配置"""
        default_config = {
            'routing_rules': [
                {
                    'name': 'datasync_success',
                    'conditions': {
                        'service': 'datasync',
                        'event_types': ['sync_success', 'cleanup_success'],
                        'levels': ['info']
                    },
                    'webhook': {
                        'type': 'feishu',
                        'url': 'YOUR_SUCCESS_WEBHOOK_URL',
                        'silent': True,
                        'at_users': []
                    }
                },
                {
                    'name': 'datasync_failure',
                    'conditions': {
                        'service': 'datasync', 
                        'event_types': ['sync_failure', 'cleanup_failure'],
                        'levels': ['error', 'critical']
                    },
                    'webhook': {
                        'type': 'feishu',
                        'url': 'YOUR_ALERT_WEBHOOK_URL',
                        'silent': False,
                        'at_users': ['@all']
                    }
                },
                {
                    'name': 'system_critical',
                    'conditions': {
                        'levels': ['critical']
                    },
                    'webhook': {
                        'type': 'feishu',
                        'url': 'YOUR_EMERGENCY_WEBHOOK_URL',
                        'silent': False,
                        'at_users': ['@all']
                    }
                }
            ]
        }
        
        # 解析默认规则
        self.route_rules = []
        for rule_data in default_config['routing_rules']:
            rule = self._parse_route_rule(rule_data)
            if rule:
                self.route_rules.append(rule)
        
        # 保存默认配置文件
        try:
            with open(self.webhooks_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            self.logger.info(f"创建默认webhook配置: {self.webhooks_config_path}")
        except Exception as e:
            self.logger.error(f"创建默认webhook配置失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if key == 'server':
            return self.server_config
        elif key in self.general_config:
            return self.general_config[key]
        else:
            return default
    
    def get_matching_rules(self, event: Dict[str, Any]) -> List[RouteRule]:
        """获取匹配事件的路由规则"""
        import logging
        logger = logging.getLogger('monitor.config.debug')
        
        logger.info(f"=== 获取匹配规则 ===")
        logger.info(f"总规则数量: {len(self.route_rules)}")
        logger.info(f"事件数据: {event}")
        
        matching_rules = []
        
        for i, rule in enumerate(self.route_rules):
            logger.info(f"规则 {i}: name={rule.name}, enabled={rule.enabled}")
            if rule.enabled and rule.conditions.matches(event):
                matching_rules.append(rule)
        
        logger.info(f"匹配的规则数量: {len(matching_rules)}")
        return matching_rules
    
    async def reload_config(self):
        """重新加载配置"""
        self.logger.info("重新加载配置...")
        await self.load_configs()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            'server': self.server_config,
            'route_rules_count': len(self.route_rules),
            'enabled_rules_count': len([r for r in self.route_rules if r.enabled]),
            'route_rules': [
                {
                    'name': rule.name,
                    'enabled': rule.enabled,
                    'service': rule.conditions.service,
                    'event_types': rule.conditions.event_types,
                    'levels': rule.conditions.levels,
                    'webhook_type': rule.webhook.type
                }
                for rule in self.route_rules
            ]
        }