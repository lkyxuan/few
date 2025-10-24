#!/usr/bin/env python3
"""
加密货币图片缓存脚本
批量下载并缓存所有加密货币的图标
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
import httpx
from urllib.parse import urlparse
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.connection import init_database, close_database, get_db_session
from services.coin_service import CoinService
from sqlalchemy import text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
CACHE_DIR = Path("/databao/dataview/backend/static/coin-images")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 默认占位符图片
DEFAULT_PLACEHOLDER = """iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA3XAAA"""

class ImageCacheManager:
    def __init__(self):
        # 增加超时时间，添加重试配置
        timeout_config = httpx.Timeout(
            timeout=60.0,  # 总超时60秒
            connect=10.0,  # 连接超时10秒
            read=50.0      # 读取超时50秒
        )
        self.client = httpx.AsyncClient(
            timeout=timeout_config,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
        )
        self.downloaded = 0
        self.failed = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def get_cache_filename(self, url: str, coin_id: str) -> str:
        """根据URL和coin_id生成缓存文件名"""
        parsed_url = urlparse(url)
        path = parsed_url.path
        ext = os.path.splitext(path)[1] if os.path.splitext(path)[1] else '.png'
        return f"{coin_id}{ext}"

    async def download_image(self, url: str, coin_id: str, max_retries: int = 3) -> bool:
        """下载单个图片，带重试机制"""
        if not url or not coin_id:
            return False

        filename = self.get_cache_filename(url, coin_id)
        file_path = CACHE_DIR / filename

        # 如果文件已存在，跳过下载
        if file_path.exists():
            logger.debug(f"Image already cached: {filename}")
            return True

        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading {coin_id} (attempt {attempt + 1}/{max_retries}): {url}")
                response = await self.client.get(url)

                if response.status_code == 200:
                    # 验证响应内容不为空
                    if len(response.content) > 0:
                        with open(file_path, 'wb') as f:
                            f.write(response.content)

                        self.downloaded += 1
                        logger.info(f"✓ Downloaded: {filename} ({len(response.content)} bytes)")
                        return True
                    else:
                        logger.warning(f"✗ Empty response for {coin_id}")
                        continue

                elif response.status_code == 404:
                    logger.warning(f"✗ Image not found for {coin_id}: HTTP 404")
                    break  # 不重试404错误
                else:
                    logger.warning(f"✗ HTTP {response.status_code} for {coin_id} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # 指数退避

            except asyncio.TimeoutError:
                logger.warning(f"✗ Timeout downloading {coin_id} (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"✗ Error downloading {coin_id} (attempt {attempt + 1}): {type(e).__name__}: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

        self.failed += 1
        return False

    async def create_placeholder(self):
        """创建默认占位符图片"""
        placeholder_path = CACHE_DIR / "placeholder.png"
        if not placeholder_path.exists():
            # 创建一个简单的32x32像素的PNG占位符
            # 这里使用一个最小的PNG图片数据
            png_data = bytes.fromhex("""
89504e470d0a1a0a0000000d494844520000002000000020080300000044a48ac40000003050
4c5445ff0000ff6600ff9900ffcc00ffff0033ff0066ff0099ff00ccff00ff3300ff3333ff3366
ff3399ff33ccff33ff6600ff6633ff6666ff6699ff66ccff66ff9900ff9933ff9966ff9999ff99
ccff99ffcc00ffcc33ffcc66ffcc99ffccccffccffff00ffff33ffff66ffff99ffffccffffff00
00000000000000000000000000000000000000000000000000000000000000000000000000
""".replace('\n', '').replace(' ', ''))

            try:
                with open(placeholder_path, 'wb') as f:
                    f.write(png_data)
                logger.info("✓ Created placeholder image")
            except Exception as e:
                logger.error(f"✗ Failed to create placeholder: {e}")

    async def cache_all_images(self, limit: int = None):
        """缓存所有币种的图片"""
        logger.info("Starting image caching process...")

        # 初始化数据库连接
        await init_database()

        try:
            # 创建占位符图片
            await self.create_placeholder()

            async with get_db_session() as db:
                coin_service = CoinService(db)

                # 获取所有币种数据
                # 直接查询数据库避免URL转换
                query = """
                SELECT DISTINCT ON (coin_id) coin_id, image, market_cap_rank
                FROM coin_data
                WHERE time >= NOW() - INTERVAL '1 day'
                  AND image IS NOT NULL
                  AND image != ''
                ORDER BY coin_id, time DESC, market_cap_rank ASC NULLS LAST
                LIMIT :limit
                """
                result = await db.execute(text(query), {"limit": limit or 10000})
                coin_rows = result.fetchall()

                total_coins = len(coin_rows)
                logger.info(f"Found {total_coins} coins to process")

                # 并发下载限制 - 减少并发数量避免超时
                semaphore = asyncio.Semaphore(3)  # 同时最多3个下载任务

                async def download_with_semaphore(coin_id, image_url):
                    async with semaphore:
                        return await self.download_image(image_url, coin_id)

                # 创建所有下载任务
                tasks = [
                    download_with_semaphore(row.coin_id, row.image)
                    for row in coin_rows
                    if row.image
                ]

                # 执行所有下载任务
                if tasks:
                    logger.info(f"Starting download of {len(tasks)} images...")
                    await asyncio.gather(*tasks, return_exceptions=True)

                logger.info(f"""
Image caching completed!
Total coins: {total_coins}
Successfully downloaded: {self.downloaded}
Failed: {self.failed}
Skipped (already cached): {total_coins - len(tasks)}
""")

        except Exception as e:
            logger.error(f"Error during caching process: {str(e)}")
            raise
        finally:
            await close_database()

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Cache cryptocurrency images")
    parser.add_argument("--limit", type=int, help="Limit number of coins to process")
    parser.add_argument("--force", action="store_true", help="Force re-download existing images")

    args = parser.parse_args()

    start_time = datetime.now()
    logger.info(f"Starting image caching at {start_time}")

    try:
        async with ImageCacheManager() as manager:
            await manager.cache_all_images(limit=args.limit)

        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Image caching completed in {duration}")

    except Exception as e:
        logger.error(f"Image caching failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # 设置环境变量
    os.environ.setdefault('LOCAL_DB_USER', 'datasync')
    os.environ.setdefault('LOCAL_DB_PASSWORD', 'datasync2025')

    asyncio.run(main())