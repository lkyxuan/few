from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from contextlib import asynccontextmanager
from settings import settings
import logging

logger = logging.getLogger(__name__)

# 数据库引擎
engine = create_async_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,  # 1小时后重新创建连接
)

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False,
)

# 数据库基类
Base = declarative_base()

# 元数据
metadata = MetaData()


@asynccontextmanager
async def get_db_session():
    """获取数据库会话的异步上下文管理器"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db():
    """获取数据库会话的依赖注入函数"""
    async with get_db_session() as session:
        yield session


async def init_database():
    """初始化数据库连接"""
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # 测试连接
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_database():
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("Database connection closed")