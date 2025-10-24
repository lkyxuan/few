#!/usr/bin/env python3
"""
DataInsight - 加密货币指标计算引擎
基于高效调度器的指标计算系统
"""

import sys
import argparse
import asyncio
from core.efficient_scheduler import SimpleEfficientScheduler
from utils.logger import setup_logger


def main():
    """DataInsight主程序入口点"""
    parser = argparse.ArgumentParser(description='DataInsight - 加密货币指标计算引擎')
    
    # 通用参数
    parser.add_argument('--config', '-c', 
                       default='/databao/datainsight/config/datainsight.yml',
                       help='配置文件路径')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='启用详细日志输出')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run: 运行指标计算
    run_parser = subparsers.add_parser('run', help='运行指标计算')
    run_parser.add_argument('--time',
                           help='指定计算时间 (例如: 2024-08-30T10:00:00Z)')
    
    # daemon: 实时监听模式
    daemon_parser = subparsers.add_parser('daemon', help='实时监听模式')
    
    # status: 查看执行状态
    status_parser = subparsers.add_parser('status', help='查看指标执行状态')
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    # 设置日志
    logger = setup_logger(verbose=args.verbose)
    
    try:
        # 初始化简化版高效调度器
        scheduler = SimpleEfficientScheduler(config_path=args.config)
        logger.info("DataInsight简化版高效调度器启动")
        
        # 执行对应命令
        if args.command == 'run':
            async def run_task():
                await scheduler.initialize()
                await scheduler.run_indicators(target_time=args.time)
                await scheduler.db_manager.close()
            asyncio.run(run_task())
            
        elif args.command == 'daemon':
            asyncio.run(scheduler.run_daemon())
            
        elif args.command == 'status':
            print(f"简化版高效调度器状态: {len(scheduler.indicators)}个指标")
            
    except Exception as e:
        logger.error(f"DataInsight执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()