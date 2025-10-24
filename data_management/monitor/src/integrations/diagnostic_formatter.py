#!/usr/bin/env python3
"""
DataBao 诊断消息格式器
生成包含完整诊断信息的监控消息，便于AI快速分析和解决问题
"""

import json
import platform
import psutil
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))

# MonitorEvent会从event_router传入，不需要直接导入


class DiagnosticFormatter:
    """诊断消息格式器"""
    
    def __init__(self):
        """初始化格式器"""
        # 系统信息缓存
        self._system_info = self._collect_system_info()
        
        # 解决方案建议库
        self._solution_hints = {
            # 同步相关问题
            "sync_failure": [
                "检查远程数据库连接状态",
                "验证数据库凭据是否正确", 
                "检查网络连通性和防火墙设置",
                "查看数据库日志确认是否有锁表或其他问题",
                "检查磁盘空间是否足够"
            ],
            "connection_error": [
                "检查数据库服务是否运行: systemctl status postgresql",
                "验证pg_hba.conf配置是否允许当前IP访问",
                "检查数据库端口是否开放: netstat -tlnp | grep 5432",
                "测试网络连通性: telnet [host] [port]"
            ],
            "permission_denied": [
                "检查用户权限: ls -la [文件路径]",
                "确认服务运行用户身份",
                "验证目录写入权限",
                "检查SELinux或AppArmor设置"
            ],
            "disk_space": [
                "检查磁盘使用情况: df -h",
                "清理日志文件: find /var/log -name '*.log*' -mtime +30",
                "清理临时文件: rm -rf /tmp/*",
                "检查并删除过期的数据备份"
            ],
            "memory_error": [
                "检查内存使用: free -h",
                "查看进程内存占用: ps aux --sort=-%mem | head",
                "检查是否有内存泄漏",
                "考虑增加swap空间或物理内存"
            ],
            "timeout_error": [
                "增加超时时间配置",
                "检查网络延迟: ping [目标主机]",
                "优化查询性能，减少执行时间",
                "检查数据库连接池配置"
            ]
        }
        
        # 关键文件路径
        self._important_paths = {
            "config": "/databao/datasync/config/",
            "logs": "/var/log/datasync/",
            "data_hot": "/databao_hot/",
            "data_warm": "/databao_warm/",
            "data_cold": "/databao_cold/"
        }
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """收集系统基础信息"""
        try:
            return {
                "hostname": platform.node(),
                "os": f"{platform.system()} {platform.release()}",
                "python": platform.python_version(),
                "architecture": platform.architecture()[0],
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception:
            return {"error": "failed_to_collect_system_info"}
    
    def format_diagnostic_message(self, event) -> str:
        """
        格式化诊断消息
        
        Args:
            event: 监控事件
            
        Returns:
            格式化的诊断消息
        """
        if event.level in ["error", "critical"]:
            return self._format_error_diagnostic(event)
        elif event.level == "warning":
            return self._format_warning_diagnostic(event)
        else:
            return self._format_info_diagnostic(event)
    
    def _format_error_diagnostic(self, event) -> str:
        """格式化错误诊断消息"""
        sections = []
        
        # 🚨 问题概述
        sections.append("🚨 **问题概述**")
        sections.append(f"**事件**: {event.event_type}")
        sections.append(f"**级别**: {event.level.upper()}")  
        sections.append(f"**消息**: {event.message}")
        sections.append(f"**时间**: {event.timestamp}")
        sections.append("")
        
        # 💻 系统环境
        sections.append("💻 **系统环境**")
        sections.append(f"**主机**: {self._system_info.get('hostname', 'unknown')}")
        sections.append(f"**系统**: {self._system_info.get('os', 'unknown')}")
        sections.append(f"**服务**: {event.service}")
        sections.append("")
        
        # ❌ 错误详情
        if event.details:
            sections.append("❌ **错误详情**")
            for key, value in event.details.items():
                if key == "error" and isinstance(value, str) and len(value) > 100:
                    # 长错误信息进行格式化
                    sections.append(f"**{key}**:")
                    sections.append("```")
                    sections.append(str(value))
                    sections.append("```")
                else:
                    sections.append(f"**{key}**: {value}")
            sections.append("")
        
        # 📊 相关指标
        if event.metrics:
            sections.append("📊 **相关指标**")
            for key, value in event.metrics.items():
                sections.append(f"**{key}**: {value}")
            sections.append("")
        
        # 🔍 诊断信息
        sections.append("🔍 **诊断信息**")
        
        # 添加实时系统状态
        try:
            current_memory = psutil.virtual_memory()
            current_cpu = psutil.cpu_percent()
            sections.append(f"**CPU使用率**: {current_cpu}%")
            sections.append(f"**内存使用率**: {current_memory.percent}%")
            sections.append(f"**内存可用**: {round(current_memory.available / (1024**3), 2)}GB")
            
            # 检查磁盘空间
            for name, path in self._important_paths.items():
                try:
                    if Path(path).exists():
                        disk_usage = psutil.disk_usage(path)
                        free_gb = disk_usage.free / (1024**3)
                        used_percent = (disk_usage.used / disk_usage.total) * 100
                        sections.append(f"**{name}磁盘**: {used_percent:.1f}% 已使用, {free_gb:.1f}GB 可用")
                except:
                    sections.append(f"**{name}磁盘**: 无法访问 {path}")
        except Exception as e:
            sections.append(f"**系统状态**: 获取失败 - {str(e)}")
        
        sections.append("")
        
        # 🛠️ 建议解决方案
        solutions = self._get_solution_hints(event)
        if solutions:
            sections.append("🛠️ **建议解决方案**")
            for i, solution in enumerate(solutions, 1):
                sections.append(f"{i}. {solution}")
            sections.append("")
        
        # 📋 调试命令
        sections.append("📋 **调试命令**")
        debug_commands = self._get_debug_commands(event)
        for desc, command in debug_commands.items():
            sections.append(f"**{desc}**: `{command}`")
        sections.append("")
        
        # 📂 相关文件路径
        sections.append("📂 **相关文件路径**")
        sections.append(f"**配置文件**: `/databao/datasync/config/datasync.yml`")
        sections.append(f"**主日志**: `/var/log/datasync/datasync.log`")
        sections.append(f"**系统日志**: `journalctl -u datasync -n 50`")
        sections.append(f"**错误日志**: `tail -n 100 /var/log/datasync/datasync.log | grep ERROR`")
        
        return "\n".join(sections)
    
    def _format_warning_diagnostic(self, event) -> str:
        """格式化警告诊断消息"""
        sections = []
        
        sections.append("⚠️ **警告通知**")
        sections.append(f"**事件**: {event.event_type}")
        sections.append(f"**消息**: {event.message}")
        sections.append(f"**时间**: {event.timestamp}")
        sections.append("")
        
        if event.details:
            sections.append("📋 **详情**")
            for key, value in event.details.items():
                sections.append(f"**{key}**: {value}")
            sections.append("")
        
        if event.metrics:
            sections.append("📊 **指标**")
            for key, value in event.metrics.items():
                sections.append(f"**{key}**: {value}")
            sections.append("")
        
        # 添加预防建议
        solutions = self._get_solution_hints(event)
        if solutions:
            sections.append("💡 **预防建议**")
            for solution in solutions[:3]:  # 只显示前3个建议
                sections.append(f"• {solution}")
        
        return "\n".join(sections)
    
    def _format_info_diagnostic(self, event) -> str:
        """格式化信息诊断消息"""
        sections = []
        
        sections.append("✅ **状态通知**")
        sections.append(f"**事件**: {event.event_type}")
        sections.append(f"**消息**: {event.message}")
        sections.append(f"**时间**: {event.timestamp}")
        
        if event.metrics:
            sections.append("")
            sections.append("📊 **执行指标**")
            for key, value in event.metrics.items():
                sections.append(f"**{key}**: {value}")
        
        return "\n".join(sections)
    
    def _get_solution_hints(self, event) -> List[str]:
        """
        获取解决方案建议
        
        Args:
            event: 监控事件
            
        Returns:
            建议列表
        """
        hints = []
        
        # 根据事件类型匹配建议
        event_type_key = event.event_type.lower()
        if event_type_key in self._solution_hints:
            hints.extend(self._solution_hints[event_type_key])
        
        # 根据错误消息匹配建议
        message_lower = event.message.lower()
        error_patterns = {
            "connection": "connection_error",
            "timeout": "timeout_error", 
            "permission denied": "permission_denied",
            "no space left": "disk_space",
            "memory": "memory_error",
            "cannot connect": "connection_error"
        }
        
        for pattern, solution_key in error_patterns.items():
            if pattern in message_lower:
                hints.extend(self._solution_hints.get(solution_key, []))
        
        # 去重并返回
        return list(dict.fromkeys(hints))
    
    def _get_debug_commands(self, event) -> Dict[str, str]:
        """
        获取调试命令
        
        Args:
            event: 监控事件
            
        Returns:
            调试命令字典
        """
        commands = {
            "检查服务状态": "systemctl status datasync",
            "查看最新日志": "journalctl -u datasync -n 20 --no-pager",
            "检查进程": "ps aux | grep datasync",
            "网络连接": "netstat -tlnp | grep 5432"
        }
        
        # 根据事件类型添加特定命令
        if "sync" in event.event_type:
            commands.update({
                "测试本地数据库": "PGPASSWORD='datasync2025' psql -h localhost -U datasync -d cryptodb -c 'SELECT 1;'",
                "测试远程数据库": "PGPASSWORD='[密码]' psql -h 95.216.186.216 -U coingecko -d timedb -c 'SELECT 1;'",
                "检查数据库连接": "netstat -an | grep :5432"
            })
        
        if "cleanup" in event.event_type:
            commands.update({
                "检查磁盘空间": "df -h",
                "查看大文件": "find /databao -size +1G -type f"
            })
        
        if "migration" in event.event_type:
            commands.update({
                "检查存储挂载": "mount | grep databao",
                "IO状态": "iostat -x 1 5"
            })
        
        return commands
    
    def format_feishu_diagnostic(self, event) -> Dict[str, Any]:
        """
        格式化飞书诊断消息
        
        Args:
            event: 监控事件
            
        Returns:
            飞书消息载荷
        """
        diagnostic_text = self.format_diagnostic_message(event)
        
        # 获取颜色和图标
        color_map = {
            "info": ("blue", "✅"),
            "warning": ("yellow", "⚠️"),
            "error": ("red", "🚨"),
            "critical": ("red", "💥")
        }
        
        color, icon = color_map.get(event.level, ("blue", "ℹ️"))
        
        payload = {
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
                            "content": diagnostic_text,
                            "tag": "lark_md"
                        }
                    },
                    {
                        "tag": "hr"
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": "💡 这条消息包含完整的诊断信息，可以直接复制给AI分析解决方案"
                            }
                        ]
                    }
                ]
            }
        }
        
        return payload