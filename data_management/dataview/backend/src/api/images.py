#!/usr/bin/env python3

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import httpx
import hashlib
import logging
from pathlib import Path
from typing import Optional
import asyncio
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# 图片缓存目录
CACHE_DIR = Path("/databao/dataview/backend/static/coin-images")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 默认占位符图片名
DEFAULT_IMAGE = "placeholder.png"

async def download_image(url: str, filename: str) -> bool:
    """异步下载图片到缓存目录"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                file_path = CACHE_DIR / filename
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded image: {filename}")
                return True
            else:
                logger.warning(f"Failed to download image {url}: HTTP {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"Error downloading image {url}: {str(e)}")
        return False

def get_cache_filename(url: str, coin_id: str) -> str:
    """根据URL和coin_id生成缓存文件名"""
    # 解析URL获取文件扩展名
    parsed_url = urlparse(url)
    path = parsed_url.path
    ext = os.path.splitext(path)[1] if os.path.splitext(path)[1] else '.png'

    # 使用coin_id作为文件名，更易于管理
    return f"{coin_id}{ext}"

@router.get("/coin/{coin_id}")
async def get_coin_image(coin_id: str, url: Optional[str] = None):
    """获取币种图片，如果本地不存在则尝试下载"""

    # 尝试常见的图片扩展名
    extensions = ['.png', '.jpg', '.jpeg', '.webp', '.svg']
    cached_file = None

    for ext in extensions:
        potential_file = CACHE_DIR / f"{coin_id}{ext}"
        if potential_file.exists():
            cached_file = potential_file
            break

    # 如果找到缓存文件，直接返回
    if cached_file:
        return FileResponse(
            cached_file,
            media_type=f"image/{cached_file.suffix[1:]}",
            headers={"Cache-Control": "public, max-age=86400"}  # 缓存1天
        )

    # 如果没有缓存且提供了URL，尝试下载
    if url:
        filename = get_cache_filename(url, coin_id)
        success = await download_image(url, filename)

        if success:
            cached_path = CACHE_DIR / filename
            if cached_path.exists():
                return FileResponse(
                    cached_path,
                    media_type=f"image/{cached_path.suffix[1:]}",
                    headers={"Cache-Control": "public, max-age=86400"}
                )

    # 返回默认占位符图片或404
    default_path = CACHE_DIR / DEFAULT_IMAGE
    if default_path.exists():
        return FileResponse(
            default_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    else:
        raise HTTPException(status_code=404, detail="Image not found")

@router.post("/cache/{coin_id}")
async def cache_coin_image(coin_id: str, url: str, background_tasks: BackgroundTasks):
    """后台缓存币种图片"""
    filename = get_cache_filename(url, coin_id)

    # 检查是否已经缓存
    cached_path = CACHE_DIR / filename
    if cached_path.exists():
        return {"status": "already_cached", "filename": filename}

    # 后台下载
    background_tasks.add_task(download_image, url, filename)

    return {"status": "download_started", "filename": filename}

@router.get("/cache/stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        cache_files = list(CACHE_DIR.glob("*"))
        total_files = len(cache_files)
        total_size = sum(f.stat().st_size for f in cache_files if f.is_file())

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "cache_dir": str(CACHE_DIR)
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")

@router.delete("/cache/clear")
async def clear_cache():
    """清空图片缓存"""
    try:
        deleted_count = 0
        for file_path in CACHE_DIR.glob("*"):
            if file_path.is_file() and file_path.name != DEFAULT_IMAGE:
                file_path.unlink()
                deleted_count += 1

        return {"status": "success", "deleted_files": deleted_count}
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")