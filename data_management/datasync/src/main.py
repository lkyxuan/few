#!/usr/bin/env python3
"""
DataSync 主程序入口
负责数据同步、清理和迁移功能的统一调度
"""

import sys
import argparse
import asyncio
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config.config_manager import ConfigManager
from logs.logger import setup_logger
from database.connection import DatabaseManager
from monitoring.monitor_client import setup_monitor_client


async def run_async_command(args, config, logger):
    """运行异步命令"""
    if args.command == 'sync':
        # DataSync主程序（智能轮询模式）
        from core.smart_scheduler import SmartSyncDaemon
        sync_daemon = SmartSyncDaemon(args.config)
        await sync_daemon.start()
        
    elif args.command == 'test':
        # 单次同步测试（不使用智能轮询）
        from core.sync_manager import SyncManager
        sync_manager = SyncManager(config)
        await sync_manager.initialize()
        await sync_manager.run(dry_run=args.dry_run)
        await sync_manager.close()
        
    elif args.command == 'cleanup':
        from cleanup.cleanup_manager import CleanupManager
        cleanup_manager = CleanupManager(config)
        await cleanup_manager.initialize()
        await cleanup_manager.run(dry_run=args.dry_run)
        await cleanup_manager.close()
        
    elif args.command == 'migrate':
        from migration.migration_manager import MigrationManager
        migration_manager = MigrationManager(config)
        await migration_manager.initialize()
        await migration_manager.run(dry_run=args.dry_run)
        await migration_manager.close()
        
    elif args.command == 'status':
        from core.sync_manager import SyncManager
        sync_manager = SyncManager(config)
        await sync_manager.initialize()
        status = await sync_manager.get_sync_status()
        print("\n=== DataSync 状态 ===")
        print(f"正在运行: {status['is_running']}")
        print(f"上次同步时间: {status['last_sync_times']}")
        print(f"配置: {status['config']}")
        await sync_manager.close()
        
    elif args.command == 'health':
        logger.info("开始健康检查...")
        
        # 检查数据库连接
        local_config = config.get_database_config('local')
        remote_config = config.get_database_config('remote')
        
        db_manager = DatabaseManager(local_config, remote_config)
        try:
            await db_manager.initialize()
            health_result = await db_manager.health_check()
            
            print("\n=== DataSync 健康检查 ===")
            print(f"本地数据库: {health_result['local_db']['status']}")
            if health_result['local_db']['status'] == 'healthy':
                print(f"  连接: ✅")
                print(f"  版本: {health_result['local_db'].get('version', 'unknown')}")
            else:
                print(f"  连接: ❌ {health_result['local_db'].get('error', '')}")
            
            print(f"远程数据库: {health_result['remote_db']['status']}")
            if health_result['remote_db']['status'] == 'healthy':
                print(f"  连接: ✅")
                print(f"  版本: {health_result['remote_db'].get('version', 'unknown')}")
            else:
                print(f"  连接: ❌ {health_result['remote_db'].get('error', '')}")
                
            logger.info("健康检查完成")
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            print(f"\n❌ 健康检查失败: {e}")
        finally:
            await db_manager.close()
            


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(description='DataSync - 数据同步工具')
    parser.add_argument('command', choices=[
        'sync', 'test', 'cleanup', 'migrate', 'status', 'health'
    ], help='要执行的命令')
    parser.add_argument('--config', '-c', default='config/datasync.yml',
                       help='配置文件路径')
    parser.add_argument('--dry-run', action='store_true',
                       help='预览模式，不实际执行')
    
    args = parser.parse_args()
    
    # 加载配置
    config = ConfigManager(args.config)
    
    # 设置日志
    logger = setup_logger(config.get('logging'))
    
    # 初始化监控客户端（如果启用）
    monitor_config = config.get('monitoring', {})
    if monitor_config.get('enabled', False):
        monitor_client = setup_monitor_client(
            service_name=monitor_config.get('service_name', 'datasync'),
            monitor_url=monitor_config.get('monitor_url', 'http://localhost:9527')
        )
        logger.info("监控客户端初始化完成")
    else:
        logger.info("监控功能已禁用")
    
    logger.info(f"DataSync启动 - 命令: {args.command}")
    
    try:
        # 运行异步命令
        asyncio.run(run_async_command(args, config, logger))
            
    except Exception as e:
        logger.error(f"执行失败: {e}")
        sys.exit(1)
        
    logger.info(f"DataSync完成 - 命令: {args.command}")


if __name__ == '__main__':
    main()