from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 数据库配置
    LOCAL_DB_HOST: str = "localhost"
    LOCAL_DB_PORT: int = 5432
    LOCAL_DB_NAME: str = "cryptodb"
    LOCAL_DB_USER: str = "datasync"
    LOCAL_DB_PASSWORD: str = "datasync2025"
    
    # API 配置
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True
    
    # CORS 配置
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://192.168.5.124:3000",
        "http://192.168.5.124:8080"
    ]
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 200
    
    # 缓存配置
    CACHE_EXPIRE_SECONDS: int = 30
    
    @property
    def database_url(self) -> str:
        """构建数据库连接 URL"""
        return (
            f"postgresql+asyncpg://{self.LOCAL_DB_USER}:{self.LOCAL_DB_PASSWORD}"
            f"@{self.LOCAL_DB_HOST}:{self.LOCAL_DB_PORT}/{self.LOCAL_DB_NAME}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()