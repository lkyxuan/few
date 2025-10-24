#!/usr/bin/env python3
"""
DataSync 数据库连接管理
处理本地和远程PostgreSQL数据库的连接池和会话管理
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from urllib.parse import quote_plus


class DatabaseManager:
    """数据库连接管理器"""
    
    def __init__(self, local_config: Dict[str, Any], remote_config: Dict[str, Any]):
        """
        初始化数据库管理器
        
        Args:
            local_config: 本地数据库配置
            remote_config: 远程数据库配置
        """
        self.local_config = local_config
        self.remote_config = remote_config
        self.logger = logging.getLogger('datasync.database')
        
        # 数据库引擎
        self._local_engine: Optional[AsyncEngine] = None
        self._remote_engine: Optional[AsyncEngine] = None
        
        # 会话工厂
        self._local_session_factory: Optional[async_sessionmaker] = None
        self._remote_session_factory: Optional[async_sessionmaker] = None
    
    async def initialize(self):
        """初始化数据库连接"""
        self.logger.info("初始化数据库连接")
        
        try:
            # 创建本地数据库引擎
            self._local_engine = self._create_engine(self.local_config, "local")
            self._local_session_factory = async_sessionmaker(
                bind=self._local_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 创建远程数据库引擎
            self._remote_engine = self._create_engine(self.remote_config, "remote")
            self._remote_session_factory = async_sessionmaker(
                bind=self._remote_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # 测试连接
            await self._test_connections()
            
            self.logger.info("数据库连接初始化成功")
            
        except Exception as e:
            self.logger.error(f"数据库连接初始化失败: {e}")
            raise
    
    def _create_engine(self, config: Dict[str, Any], db_type: str) -> AsyncEngine:
        """
        创建数据库引擎
        
        Args:
            config: 数据库配置
            db_type: 数据库类型标识
            
        Returns:
            AsyncEngine实例
        """
        # 构建连接URL
        user = quote_plus(config['user'])
        password = quote_plus(config['password'])
        host = config['host']
        port = config.get('port', 5432)
        database = config['name']
        
        # 对于asyncpg，不在URL中包含SSL参数，而是通过connect_args传递
        url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        
        # SSL配置将通过connect_args传递
        ssl_mode = config.get('ssl_mode', 'disable')
        
        # 连接池配置
        pool_size = config.get('pool_size', 10)
        
        # 异步引擎配置 - 不指定poolclass，让SQLAlchemy自动选择
        if db_type == "remote":
            # 远程数据库使用较小的连接池
            pool_kwargs = {
                'pool_size': min(pool_size, 5),
                'max_overflow': 10,
                'pool_timeout': config.get('timeout', 30),
                'pool_recycle': 3600,  # 1小时回收连接
                'pool_pre_ping': True  # 连接前测试
            }
        else:
            # 本地数据库使用较大的连接池
            pool_kwargs = {
                'pool_size': pool_size,
                'max_overflow': 20,
                'pool_timeout': 10,
                'pool_recycle': 7200,  # 2小时回收连接
                'pool_pre_ping': True
            }
        
        # 准备连接参数
        connect_args = {}
        if ssl_mode != 'disable':
            connect_args['ssl'] = ssl_mode
        
        engine = create_async_engine(
            url,
            echo=False,  # 生产环境关闭SQL日志
            future=True,
            connect_args=connect_args,
            **pool_kwargs
        )
        
        self.logger.info(f"创建{db_type}数据库引擎: {host}:{port}/{database}")
        return engine
    
    async def _test_connections(self):
        """测试数据库连接"""
        # 测试本地连接
        try:
            async with self.get_local_session() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
            self.logger.info("本地数据库连接测试通过")
        except Exception as e:
            self.logger.error(f"本地数据库连接测试失败: {e}")
            raise
        
        # 测试远程连接（可能因网络限制失败）
        try:
            async with self.get_remote_session() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
            self.logger.info("远程数据库连接测试通过")
        except Exception as e:
            self.logger.warning(f"远程数据库连接测试跳过（网络限制）: {e}")
            # 远程连接失败不影响整体测试
        
        self.logger.info("数据库连接测试完成")
    
    @asynccontextmanager
    async def get_local_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取本地数据库会话
        
        Yields:
            AsyncSession实例
        """
        if not self._local_session_factory:
            raise RuntimeError("本地数据库未初始化")
        
        async with self._local_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    @asynccontextmanager 
    async def get_remote_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取远程数据库会话
        
        Yields:
            AsyncSession实例
        """
        if not self._remote_session_factory:
            raise RuntimeError("远程数据库未初始化")
        
        async with self._remote_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_local(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        在本地数据库执行查询
        
        Args:
            query: SQL查询
            params: 查询参数
            
        Returns:
            查询结果
        """
        async with self.get_local_session() as session:
            result = await session.execute(text(query), params or {})
            return result
    
    async def execute_remote(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        在远程数据库执行查询
        
        Args:
            query: SQL查询
            params: 查询参数
            
        Returns:
            查询结果
        """
        async with self.get_remote_session() as session:
            result = await session.execute(text(query), params or {})
            return result
    
    async def get_local_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取本地表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        query = """
        SELECT 
            COUNT(*) as row_count,
            MIN(time) as min_time,
            MAX(time) as max_time
        FROM {} 
        WHERE time IS NOT NULL
        """.format(table_name)
        
        result = await self.execute_local(query)
        row = result.fetchone()
        
        return {
            'table_name': table_name,
            'row_count': row[0] if row else 0,
            'min_time': row[1] if row and row[1] else None,
            'max_time': row[2] if row and row[2] else None
        }
    
    async def get_remote_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        获取远程表信息
        
        Args:
            table_name: 表名
            
        Returns:
            表信息字典
        """
        query = """
        SELECT 
            COUNT(*) as row_count,
            MIN(time) as min_time,
            MAX(time) as max_time
        FROM {} 
        WHERE time IS NOT NULL
        """.format(table_name)
        
        result = await self.execute_remote(query)
        row = result.fetchone()
        
        return {
            'table_name': table_name,
            'row_count': row[0] if row else 0,
            'min_time': row[1] if row and row[1] else None,
            'max_time': row[2] if row and row[2] else None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态字典
        """
        health_status = {
            'local_db': {'status': 'unknown', 'latency': None},
            'remote_db': {'status': 'unknown', 'latency': None}
        }
        
        # 检查本地数据库
        try:
            import time
            start_time = time.time()
            async with self.get_local_session() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000  # 毫秒
            health_status['local_db'] = {'status': 'healthy', 'latency': latency}
        except Exception as e:
            health_status['local_db'] = {'status': 'unhealthy', 'error': str(e)}
        
        # 检查远程数据库
        try:
            start_time = time.time()
            async with self.get_remote_session() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.time() - start_time) * 1000  # 毫秒
            health_status['remote_db'] = {'status': 'healthy', 'latency': latency}
        except Exception as e:
            health_status['remote_db'] = {'status': 'unhealthy', 'error': str(e)}
        
        return health_status
    
    async def close(self):
        """关闭数据库连接"""
        self.logger.info("关闭数据库连接")
        
        if self._local_engine:
            await self._local_engine.dispose()
        
        if self._remote_engine:
            await self._remote_engine.dispose()
        
        self.logger.info("数据库连接已关闭")