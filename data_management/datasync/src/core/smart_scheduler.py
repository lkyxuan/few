#!/usr/bin/env python3
"""
DataSync 智能调度管理器
基于绝对时间窗口的高效轮询机制
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Callable, Optional


class SmartScheduler:
    """
    智能调度管理器 - 绝对时间窗口轮询策略
    
    基于数据采集规律的智能轮询：
    - 数据每3分钟采集一次（0:00, 3:00, 6:00...）
    - 采集耗时约10秒，数据约在0:10, 3:10, 6:10到达
    - 轮询窗口：每3分钟周期的第5-30秒（0:05-0:30, 3:05-3:30...）
    - 窗口内高频轮询，发现数据立即同步并结束轮询
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
        
        # 获取智能轮询配置
        smart_polling_config = self.config.get('smart_polling', {})
        
        # 轮询窗口配置
        self.cycle_minutes = smart_polling_config.get('polling_cycle_minutes', 3)  # 3分钟周期
        self.window_start_seconds = smart_polling_config.get('polling_window_start', 5)  # 第5秒开始
        self.window_end_seconds = smart_polling_config.get('polling_window_end', 30)  # 第30秒结束  
        self.polling_interval = smart_polling_config.get('polling_interval_seconds', 2)  # 每2秒轮询一次
        
        # 状态管理
        self.is_running = False
        self.current_cycle_data_found = False
        self.last_successful_sync_time = None
        
        self.logger.info(f"智能调度器初始化完成")
        self.logger.info(f"• 轮询周期: {self.cycle_minutes}分钟")
        self.logger.info(f"• 轮询窗口: 第{self.window_start_seconds}-{self.window_end_seconds}秒") 
        self.logger.info(f"• 轮询间隔: {self.polling_interval}秒")
    
    async def start_smart_polling(self):
        """开始智能轮询"""
        if self.is_running:
            self.logger.warning("智能调度器已在运行中")
            return
        
        self.is_running = True
        self.logger.info("🚀 启动智能轮询调度器")
        
        try:
            while self.is_running:
                # 计算下一个轮询窗口
                next_window_start = self._calculate_next_polling_window()
                
                # 等待到轮询窗口开始
                await self._wait_until(next_window_start)
                
                if not self.is_running:
                    break
                
                # 执行轮询窗口
                await self._execute_polling_window()
                
        except Exception as e:
            self.logger.error(f"智能调度器运行异常: {e}")
        finally:
            self.is_running = False
            self.logger.info("智能调度器已停止")
    
    def _calculate_next_polling_window(self) -> datetime:
        """
        计算下一个轮询窗口的开始时间
        
        Returns:
            下一个轮询窗口的开始时间
        """
        now = datetime.now(timezone.utc)
        
        # 计算当前所在的3分钟周期
        minutes_since_hour = now.minute
        current_cycle = (minutes_since_hour // self.cycle_minutes) * self.cycle_minutes
        
        # 计算当前周期的轮询窗口开始时间
        current_window_start = now.replace(
            minute=current_cycle,
            second=self.window_start_seconds,
            microsecond=0
        )
        
        # 如果当前时间已经过了当前周期的轮询窗口，计算下一个周期
        if now > current_window_start.replace(second=self.window_end_seconds):
            next_cycle = (current_cycle + self.cycle_minutes) % 60
            if next_cycle < current_cycle:  # 跨小时
                current_window_start = current_window_start.replace(
                    hour=(current_window_start.hour + 1) % 24,
                    minute=next_cycle
                )
            else:
                current_window_start = current_window_start.replace(minute=next_cycle)
        elif now < current_window_start:
            # 当前时间在轮询窗口开始之前，使用当前周期
            pass
        else:
            # 当前时间在轮询窗口内，立即开始
            return now
        
        return current_window_start
    
    async def _wait_until(self, target_time: datetime):
        """等待到指定时间"""
        now = datetime.now(timezone.utc)
        wait_seconds = (target_time - now).total_seconds()
        
        if wait_seconds > 0:
            self.logger.info(f"⏰ 等待轮询窗口开始: {target_time.strftime('%H:%M:%S')} "
                           f"(还需等待 {wait_seconds:.1f}秒)")
            await asyncio.sleep(wait_seconds)
    
    async def _execute_polling_window(self):
        """执行轮询窗口"""
        window_start = datetime.now(timezone.utc)
        cycle_start_minute = (window_start.minute // self.cycle_minutes) * self.cycle_minutes
        
        self.logger.info(f"🔍 开始轮询窗口 [{cycle_start_minute:02d}:{self.window_start_seconds:02d}-"
                        f"{cycle_start_minute:02d}:{self.window_end_seconds:02d}]")
        
        self.current_cycle_data_found = False
        polling_count = 0
        
        # 计算轮询窗口结束时间
        window_end = window_start.replace(second=self.window_end_seconds, microsecond=0)
        if window_start.second > self.window_end_seconds:
            window_end = window_end + timedelta(minutes=self.cycle_minutes)
        
        while datetime.now(timezone.utc) < window_end and self.is_running:
            polling_count += 1
            
            # 检查是否有新数据
            has_new_data = await self._check_for_new_data()
            
            if has_new_data:
                self.logger.info(f"✅ 第{polling_count}次轮询发现新数据，立即开始同步")
                
                # 执行同步
                await self._execute_sync()
                
                # 标记当前周期已找到数据，结束轮询窗口
                self.current_cycle_data_found = True
                break
            
            # 等待下次轮询
            await asyncio.sleep(self.polling_interval)
        
        if not self.current_cycle_data_found:
            elapsed_time = (datetime.now(timezone.utc) - window_start).total_seconds()
            self.logger.info(f"🔍 轮询窗口结束，共轮询{polling_count}次，"
                           f"耗时{elapsed_time:.1f}秒，未发现新数据")
    
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
            
            self.logger.info(f"✅ 智能轮询触发同步完成，耗时{sync_duration:.2f}秒")
            
        except Exception as e:
            self.logger.error(f"智能轮询触发同步失败: {e}")
    
    async def stop(self):
        """停止智能调度器"""
        self.logger.info("正在停止智能调度器...")
        self.is_running = False
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        now = datetime.now(timezone.utc)
        next_window = self._calculate_next_polling_window()
        
        return {
            'is_running': self.is_running,
            'current_time': now.strftime('%H:%M:%S'),
            'next_polling_window': next_window.strftime('%H:%M:%S'),
            'seconds_until_next_window': (next_window - now).total_seconds(),
            'last_successful_sync': (
                self.last_successful_sync_time.strftime('%H:%M:%S') 
                if self.last_successful_sync_time else None
            ),
            'polling_config': {
                'cycle_minutes': self.cycle_minutes,
                'window_start_seconds': self.window_start_seconds,
                'window_end_seconds': self.window_end_seconds,
                'polling_interval': self.polling_interval
            }
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