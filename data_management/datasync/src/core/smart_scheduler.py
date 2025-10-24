#!/usr/bin/env python3
"""
DataSync 智能调度管理器
简化的定时同步机制
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any


class SmartScheduler:
    """
    智能调度管理器 - 简化版本
    
    基于配置的定时同步：
    - 按照配置的间隔时间定期检查新数据
    - 发现新数据立即同步
    """
    
    def __init__(self, sync_manager, config_manager):
        """
        初始化智能调度器
        
        Args:
            sync_manager: 同步管理器实例
            config_manager: 配置管理器实例
        """
        self.sync_manager = sync_manager
        self.config = config_manager
        self.logger = logging.getLogger('datasync.scheduler')
        
        # 获取同步配置
        sync_config = self.config.get('sync', {})
        self.interval_minutes = sync_config.get('interval_minutes', 3)  # 默认3分钟
        
        # 状态管理
        self.is_running = False
        self.last_successful_sync_time = None
        
        self.logger.info(f"智能调度器初始化完成，同步间隔: {self.interval_minutes}分钟")
    
    async def start_smart_polling(self):
        """开始智能轮询"""
        if self.is_running:
            self.logger.warning("智能调度器已在运行中")
            return
        
        self.is_running = True
        self.logger.info("🚀 启动智能调度器")
        
        try:
            while self.is_running:
                # 检查是否有新数据
                has_new_data = await self._check_for_new_data()
                
                if has_new_data:
                    self.logger.info("✅ 发现新数据，开始同步")
                    await self._execute_sync()
                else:
                    self.logger.debug("暂无新数据，等待下次检查")
                
                # 等待下次检查
                await asyncio.sleep(self.interval_minutes * 60)
                
        except Exception as e:
            self.logger.error(f"智能调度器运行异常: {e}")
        finally:
            self.is_running = False
            self.logger.info("智能调度器已停止")
    
    async def _check_for_new_data(self) -> bool:
        """
        检查是否有新数据需要同步
        
        Returns:
            是否有新数据
        """
        try:
            # 获取远程数据库的记录数量（基于上次同步时间）
            last_sync_time = None
            if hasattr(self.sync_manager, 'last_sync_times'):
                last_sync_time = self.sync_manager.last_sync_times.get('coin_data')
            
            new_records_count = await self.sync_manager._get_remote_records_count(
                'coin_data', last_sync_time
            )
            
            return new_records_count > 0
            
        except Exception as e:
            self.logger.warning(f"检查新数据时出错: {e}")
            return False
    
    async def _execute_sync(self):
        """执行数据同步"""
        try:
            sync_start_time = time.time()
            
            # 执行同步
            await self.sync_manager.run()
            
            sync_duration = time.time() - sync_start_time
            self.last_successful_sync_time = datetime.now(timezone.utc)
            
            self.logger.info(f"✅ 同步完成，耗时{sync_duration:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"同步失败: {e}")
    
    async def stop(self):
        """停止智能调度器"""
        self.logger.info("正在停止智能调度器...")
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            'is_running': self.is_running,
            'interval_minutes': self.interval_minutes,
            'last_successful_sync': (
                self.last_successful_sync_time.strftime('%H:%M:%S') 
                if self.last_successful_sync_time else None
            )
        }


class SmartSyncDaemon:
    """智能同步守护进程"""
    
    def __init__(self, config_path: str):
        """
        初始化守护进程
        
        Args:
            config_path: 配置文件路径
        """
        from ..config.config_manager import ConfigManager
        from ..core.sync_manager import SyncManager
        from .logs.logger import setup_logger
        
        self.config = ConfigManager(config_path)
        self.logger = setup_logger(self.config.get('logging'))
        
        # 创建同步管理器和智能调度器
        self.sync_manager = None
        self.scheduler = None
    
    async def start(self):
        """启动守护进程"""
        self.logger.info("🚀 启动DataSync智能同步守护进程")
        
        try:
            # 初始化同步管理器
            from ..core.sync_manager import SyncManager
            self.sync_manager = SyncManager(self.config)
            await self.sync_manager.initialize()
            
            # 创建智能调度器
            self.scheduler = SmartScheduler(self.sync_manager, self.config)
            
            # 启动智能轮询
            await self.scheduler.start_smart_polling()
            
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        except Exception as e:
            self.logger.error(f"守护进程运行异常: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        if self.scheduler:
            await self.scheduler.stop()
        
        if self.sync_manager:
            await self.sync_manager.close()
        
        self.logger.info("资源清理完成")


# CLI支持
if __name__ == '__main__':
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='DataSync智能调度器')
    parser.add_argument('--config', '-c', default='config/datasync.yml',
                       help='配置文件路径')
    
    args = parser.parse_args()
    
    daemon = SmartSyncDaemon(args.config)
    
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序异常退出: {e}")
        sys.exit(1)