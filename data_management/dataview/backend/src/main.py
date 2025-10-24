#!/usr/bin/env python3

import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from settings import settings
from database.connection import init_database, close_database
from api.coins import router as coins_router
from api.market import router as market_router
from api.images import router as images_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    logger.info("Initializing database connection...")
    try:
        await init_database()
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # 关闭时清理资源
    logger.info("Closing database connection...")
    await close_database()
    logger.info("Database connection closed")


# 创建 FastAPI 应用
app = FastAPI(
    title="DataBao DataView API",
    description="DataBao 平台前端数据接口服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)

# 注册路由
app.include_router(coins_router, prefix=settings.API_V1_PREFIX)
app.include_router(market_router, prefix=settings.API_V1_PREFIX)
app.include_router(images_router, prefix=settings.API_V1_PREFIX)


# 根路径
@app.get("/", tags=["root"])
async def root():
    """API 根路径"""
    return {
        "message": "DataBao DataView API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_check": "/health"
    }


# 健康检查
@app.get("/health", tags=["health"])
async def health_check():
    """健康检查接口"""
    try:
        # 这里可以添加数据库连接检查等
        return {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00Z",
            "version": "1.0.0",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误，请稍后重试",
                "details": {}
            }
        }
    )


def main():
    """主函数"""
    logger.info(f"Starting DataView API server on {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Database URL: {settings.database_url}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()