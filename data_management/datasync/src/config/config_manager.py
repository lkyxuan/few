#!/usr/bin/env python3
"""
DataSync 配置管理器
处理YAML配置文件和环境变量解析
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import re


class ConfigManager:
    """配置管理器，支持YAML配置文件和环境变量替换"""
    
    def __init__(self, config_path: str):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            # 递归处理环境变量替换
            self._config = self._resolve_env_vars(raw_config)
            
        except Exception as e:
            logging.error(f"配置文件加载失败: {e}")
            raise
    
    def _resolve_env_vars(self, obj: Any) -> Any:
        """
        递归解析配置中的环境变量
        支持格式: ${VAR_NAME} 或 ${VAR_NAME:-default_value}
        """
        if isinstance(obj, dict):
            return {k: self._resolve_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_var(obj)
        else:
            return obj
    
    def _substitute_env_var(self, value: str) -> str:
        """
        替换字符串中的环境变量
        
        Args:
            value: 包含环境变量的字符串
            
        Returns:
            替换后的字符串
        """
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            
            # 获取环境变量值
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            elif default_value:
                return default_value.lstrip('-')  # 移除默认值前的 '-'
            else:
                logging.warning(f"环境变量 {var_name} 未设置且无默认值")
                return f"${{{var_name}}}"  # 保持原样
        
        return re.sub(pattern, replace_match, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        
        Args:
            key: 配置键，支持 'database.local.host' 格式
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_database_config(self, db_type: str) -> Dict[str, Any]:
        """
        获取数据库配置
        
        Args:
            db_type: 数据库类型 ('local' 或 'remote')
            
        Returns:
            数据库配置字典
        """
        return self.get(f'database.{db_type}', {})
    
    def get_sync_config(self) -> Dict[str, Any]:
        """获取同步配置"""
        return self.get('sync', {})
    
    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self.get('storage', {})
    
    def get_migration_config(self) -> Dict[str, Any]:
        """获取数据迁移配置"""
        return self.get('migration', {})
    
    def get_cleanup_config(self) -> Dict[str, Any]:
        """获取远程清理配置"""
        return self.get('remote_cleanup', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def validate_config(self) -> bool:
        """
        验证配置的完整性
        
        Returns:
            配置是否有效
        """
        required_sections = [
            'database.local.host',
            'database.local.user', 
            'database.local.password',
            'database.remote.host',
            'database.remote.user',
            'database.remote.password',
        ]
        
        missing_keys = []
        for key in required_sections:
            if self.get(key) is None:
                missing_keys.append(key)
        
        if missing_keys:
            logging.error(f"配置验证失败，缺少必需的配置项: {missing_keys}")
            return False
        
        return True
    
    def reload(self):
        """重新加载配置文件"""
        logging.info("重新加载配置文件")
        self._load_config()
    
    def __str__(self) -> str:
        """返回配置的字符串表示（隐藏敏感信息）"""
        safe_config = self._mask_sensitive_data(self._config.copy())
        return yaml.dump(safe_config, default_flow_style=False, allow_unicode=True)
    
    def _mask_sensitive_data(self, obj: Any) -> Any:
        """递归隐藏敏感数据"""
        sensitive_keys = {'password', 'secret', 'key', 'token'}
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if any(sensitive in k.lower() for sensitive in sensitive_keys):
                    result[k] = '***'
                else:
                    result[k] = self._mask_sensitive_data(v)
            return result
        elif isinstance(obj, list):
            return [self._mask_sensitive_data(item) for item in obj]
        else:
            return obj