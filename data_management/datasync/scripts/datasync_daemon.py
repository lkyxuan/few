#!/usr/bin/env python3
"""
DataSync 守护进程
提供服务启动、停止、重载功能
"""

import os
import sys
import time
import signal
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# 添加src路径
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir / 'src'))

from config.config_manager import ConfigManager
from core.sync_manager import SyncManager
from cleanup.cleanup_manager import CleanupManager  
from migration.migration_manager import MigrationManager
from logs.logger import setup_logger
from monitoring.monitor_client import setup_monitor_client
from database.connection import DatabaseManager


class DataSyncDaemon:
    """DataSync守护进程"""
    
    def __init__(self):
        self.config = None
        self.logger = None
        self.sync_manager = None
        self.cleanup_manager = None
        self.migration_manager = None
        self.monitor_interface = None
        self.db_manager = None
        self.running = False
        self.pid_file = '/var/run/datasync/datasync.pid'
        
        # 信号处理
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGHUP, self._reload_handler)
    
    async def initialize(self):
        """初始化守护进程"""
        try:
            # 加载配置
            config_path = current_dir / 'config' / 'datasync.yml'
            self.config = ConfigManager(str(config_path))
            
            # 设置日志
            log_config = self.config.get_logging_config()
            
            # 确保日志目录存在
            log_dir = Path(log_config['file']).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger = setup_logger(log_config)
            self.logger.info("DataSync守护进程启动")
            
            # 初始化数据库管理器
            local_config = self.config.get_database_config('local')
            remote_config = self.config.get_database_config('remote')
            self.db_manager = DatabaseManager(local_config, remote_config)
            await self.db_manager.initialize()
            
            # 设置监控客户端
            self.monitor_interface = setup_monitor_client()
            
            # 初始化管理器（传入监控接口）
            self.sync_manager = SyncManager(self.config, self.monitor_interface)
            await self.sync_manager.initialize()
            
            self.cleanup_manager = CleanupManager(self.config, self.monitor_interface)
            await self.cleanup_manager.initialize()
            
            self.migration_manager = MigrationManager(self.config, self.monitor_interface)
            await self.migration_manager.initialize()
            
            self.logger.info("守护进程初始化完成")
            
        except Exception as e:
            print(f"守护进程初始化失败: {e}")
            sys.exit(1)
    
    async def run_sync_loop(self):
        """运行同步循环"""
        self.running = True
        
        # 解析同步间隔
        interval_str = self.config.get('sync.interval', '3m')
        interval_seconds = self._parse_interval(interval_str)
        
        self.logger.info(f"开始同步循环，间隔: {interval_seconds}秒")
        
        last_cleanup_time = datetime.min
        last_migration_time = datetime.min
        
        while self.running:
            try:
                # 发出服务状态事件
                await self.monitor_interface.service_status(
                    message=f"🔄 DataSync服务运行中 (间隔: {interval_seconds//60}分钟)",
                    details={
                        "service_name": "datasync",
                        "sync_interval_minutes": interval_seconds // 60,
                        "status": "active"
                    },
                    metrics={
                        "sync_interval_seconds": interval_seconds,
                        "loop_count": getattr(self, '_loop_count', 0)
                    }
                )
                # 增加循环计数器
                self._loop_count = getattr(self, '_loop_count', 0) + 1
                
                # 执行数据同步
                await self.sync_manager.run()
                
                # 检查是否需要清理（同步后自动触发）
                cleanup_config = self.config.get_cleanup_config()
                if cleanup_config.get('trigger_after_sync', False):
                    now = datetime.utcnow()
                    # 限制清理频率（最多每小时一次）
                    if (now - last_cleanup_time).total_seconds() > 3600:
                        await self.cleanup_manager.run()
                        last_cleanup_time = now
                
                # 检查是否需要迁移（每天检查一次）
                now = datetime.utcnow()
                if (now - last_migration_time).total_seconds() > 86400:  # 24小时
                    await self.migration_manager.run()
                    last_migration_time = now
                
                # 等待下次同步
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                self.logger.error(f"同步循环出错: {e}", exc_info=True)
                # 出错后等待较短时间重试
                await asyncio.sleep(60)
    
    def _parse_interval(self, interval_str: str) -> int:
        """解析时间间隔字符串"""
        if interval_str.endswith('s'):
            return int(interval_str[:-1])
        elif interval_str.endswith('m'):
            return int(interval_str[:-1]) * 60
        elif interval_str.endswith('h'):
            return int(interval_str[:-1]) * 3600
        else:
            return int(interval_str)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"接收到信号 {signum}，准备停止服务")
        self.running = False
    
    def _reload_handler(self, signum, frame):
        """重载处理器"""
        self.logger.info("接收到重载信号，重新加载配置")
        try:
            self.config.reload()
            self.logger.info("配置重载完成")
        except Exception as e:
            self.logger.error(f"配置重载失败: {e}")
    
    def _create_pid_file(self):
        """创建PID文件"""
        try:
            pid_dir = Path(self.pid_file).parent
            pid_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            
        except Exception as e:
            print(f"创建PID文件失败: {e}")
    
    def _remove_pid_file(self):
        """删除PID文件"""
        try:
            if Path(self.pid_file).exists():
                os.remove(self.pid_file)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"删除PID文件失败: {e}")
    
    def _is_running(self) -> bool:
        """检查进程是否正在运行"""
        try:
            if not Path(self.pid_file).exists():
                return False
            
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
                
        except Exception:
            return False
    
    def start(self):
        """启动守护进程"""
        if self._is_running():
            print("DataSync已在运行中")
            return
        
        print("启动DataSync守护进程...")
        
        # 创建PID文件
        self._create_pid_file()
        
        try:
            # 运行主循环
            asyncio.run(self._run_daemon())
        except Exception as e:
            print(f"守护进程运行失败: {e}")
        finally:
            self._remove_pid_file()
    
    async def _run_daemon(self):
        """运行守护进程主逻辑"""
        await self.initialize()
        await self.run_sync_loop()
        
        # 清理资源
        if self.sync_manager:
            await self.sync_manager.close()
        if self.cleanup_manager:
            await self.cleanup_manager.close()
        if self.migration_manager:
            await self.migration_manager.close()
        if self.db_manager:
            await self.db_manager.close()
        
        self.logger.info("DataSync守护进程已停止")
    
    def stop(self):
        """停止守护进程"""
        try:
            if not Path(self.pid_file).exists():
                print("DataSync未运行")
                return
            
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"停止DataSync守护进程 (PID: {pid})")
            
            # 发送TERM信号
            os.kill(pid, signal.SIGTERM)
            
            # 等待进程停止
            for _ in range(30):
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except OSError:
                    break
            else:
                # 如果还在运行，发送KILL信号
                print("强制停止进程...")
                os.kill(pid, signal.SIGKILL)
            
            self._remove_pid_file()
            print("DataSync已停止")
            
        except Exception as e:
            print(f"停止服务失败: {e}")
    
    def reload(self):
        """重载配置"""
        try:
            if not Path(self.pid_file).exists():
                print("DataSync未运行")
                return
            
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            print(f"重载DataSync配置 (PID: {pid})")
            os.kill(pid, signal.SIGHUP)
            print("配置重载信号已发送")
            
        except Exception as e:
            print(f"重载配置失败: {e}")


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: datasync_daemon.py {start|stop|reload}")
        sys.exit(1)
    
    command = sys.argv[1]
    daemon = DataSyncDaemon()
    
    if command == 'start':
        daemon.start()
    elif command == 'stop':
        daemon.stop()
    elif command == 'reload':
        daemon.reload()
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()