#!/usr/bin/env python3
"""
DataBao 独立监控服务
提供集中式的监控事件处理、webhook路由和管理界面
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from api.monitor_api import create_monitor_app
from core.event_router import EventRouter
from core.config_manager import ConfigManager
from integrations.webhook_router import WebhookRouter


class MonitorService:
    """监控服务主类"""
    
    def __init__(self):
        """初始化监控服务"""
        self.logger = self._setup_logger()
        self.config_manager = None
        self.event_router = None
        self.webhook_router = None
        self.app = None
        self._shutdown_event = asyncio.Event()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('/var/log/databao/monitor.log', 'a')
            ]
        )
        return logging.getLogger('databao.monitor')
    
    async def initialize(self):
        """初始化所有组件"""
        try:
            self.logger.info("初始化DataBao监控服务...")
            
            # 初始化配置管理器
            self.config_manager = ConfigManager()
            await self.config_manager.load_configs()
            
            # 初始化Webhook路由器
            self.webhook_router = WebhookRouter(
                config_path='/databao/monitor/config/webhooks.yml'
            )
            await self.webhook_router.load_config()
            
            # 初始化事件路由器
            self.event_router = EventRouter(
                webhook_router=self.webhook_router
            )
            
            # 创建Web应用
            self.app = create_monitor_app(
                event_router=self.event_router,
                config_manager=self.config_manager
            )
            
            self.logger.info("监控服务初始化完成")
            
        except Exception as e:
            self.logger.error(f"监控服务初始化失败: {e}")
            raise
    
    async def start(self):
        """启动监控服务"""
        try:
            await self.initialize()
            
            # 获取服务配置
            server_config = self.config_manager.get('server', {
                'host': '0.0.0.0',
                'port': 9527
            })
            
            host = server_config.get('host', '0.0.0.0')
            port = server_config.get('port', 9527)
            
            self.logger.info(f"启动监控服务 - {host}:{port}")
            
            # 设置信号处理
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGINT, signal.SIGTERM]:
                loop.add_signal_handler(sig, self._signal_handler)
            
            # 启动Web服务器
            import uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                loop="asyncio"
            )
            server = uvicorn.Server(config)
            
            # 启动服务器（非阻塞）
            server_task = asyncio.create_task(server.serve())
            
            self.logger.info(f"监控服务已启动，访问地址: http://{host}:{port}")
            self.logger.info(f"管理界面: http://{host}:{port}/dashboard")
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
            # 优雅关闭
            self.logger.info("正在关闭监控服务...")
            server.should_exit = True
            await server_task
            
        except Exception as e:
            self.logger.error(f"监控服务启动失败: {e}")
            raise
    
    def _signal_handler(self):
        """信号处理器"""
        self.logger.info("收到关闭信号")
        self._shutdown_event.set()
    
    async def health_check(self):
        """健康检查"""
        try:
            status = {
                "service": "DataBao Monitor",
                "status": "healthy",
                "components": {
                    "config_manager": "healthy" if self.config_manager else "not_initialized",
                    "event_router": "healthy" if self.event_router else "not_initialized", 
                    "webhook_router": "healthy" if self.webhook_router else "not_initialized"
                }
            }
            
            # 检查webhook连通性
            if self.webhook_router:
                webhook_status = await self.webhook_router.health_check()
                status["components"]["webhooks"] = webhook_status
            
            return status
            
        except Exception as e:
            return {
                "service": "DataBao Monitor",
                "status": "unhealthy",
                "error": str(e)
            }


async def main():
    """主函数"""
    service = MonitorService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        print("\n监控服务已停止")
    except Exception as e:
        print(f"监控服务运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 确保日志目录存在
    Path('/var/log/databao').mkdir(parents=True, exist_ok=True)
    
    # 运行监控服务
    asyncio.run(main())