
import logging
import time
import psycopg2
from psycopg2.extras import execute_values
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Dict, Any, Set

# 从配置模块导入常量
from config import DB_CONFIG, DB_CONNECT_RETRIES, COINS_PER_PAGE
# 从工具模块导入函数和常量
from utils import align_time_to_3min, datetime_to_ms_timestamp


@contextmanager
def get_db_connection():
    """获取数据库连接的上下文管理器，支持重试"""
    conn = None
    try:
        for attempt in range(DB_CONNECT_RETRIES):
            try:
                conn = psycopg2.connect(**DB_CONFIG)
                logging.debug("数据库连接成功")
                break
            except psycopg2.Error as e:
                logging.error(f"数据库连接失败 (尝试 {attempt + 1}/{DB_CONNECT_RETRIES}): {e}")
                if attempt == DB_CONNECT_RETRIES - 1:
                    raise  # 达到最大重试次数，抛出异常
                time.sleep(2 ** attempt)  # 指数退避

        if conn is None:
            raise ConnectionError("无法建立数据库连接")

        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
                logging.debug("数据库连接已关闭")
            except Exception as e:
                logging.error(f"关闭数据库连接时出错: {e}")


def verify_database_save(conn, aligned_ms_timestamp: int, expected_coins: Set[str]) -> bool:
    """验证数据是否正确保存到数据库（使用毫秒时间戳）"""
    if not expected_coins:
        logging.warning("没有需要验证的币种 (expected_coins 为空)")
        return True

    try:
        with conn.cursor() as cur:
            # 数据库字段 time 必须是 BIGINT
            cur.execute("""
                SELECT coin_id
                FROM coin_data
                WHERE time = %s AND coin_id = ANY(%s)
            """, (aligned_ms_timestamp, list(expected_coins)))

            saved_coins = {row[0] for row in cur.fetchall()}

            missing_coins = expected_coins - saved_coins

            # 将毫秒时间戳转换为 datetime 用于日志 (可选)
            log_time = datetime.fromtimestamp(aligned_ms_timestamp / 1000, tz=timezone.utc)

            if missing_coins:
                logging.error(
                    f"数据库验证失败: 在 {log_time.strftime('%Y-%m-%d %H:%M:%S.%f %Z')} 缺少 {len(missing_coins)} 个币种. 示例: {list(missing_coins)[:5]}")
                return False

            logging.debug(
                f"数据库验证成功: {len(saved_coins)}/{len(expected_coins)} 个币种已保存 (时间: {log_time.strftime('%Y-%m-%d %H:%M:%S.%f %Z')})")
            return True

    except Exception as e:
        logging.error(f"验证数据库保存时出错: {e}")
        return False


def save_to_database(data: List[Dict[Any, Any]], conn, current_time: datetime) -> bool:
    """保存数据到数据库，返回是否成功（使用毫秒时间戳）"""
    if not data:
        logging.warning("没有数据需要保存 (data为空)")
        return False

    # 1. 转换当前时间为毫秒时间戳
    raw_ms_timestamp = datetime_to_ms_timestamp(current_time)

    # 2. 对齐时间 (假设 align_time_to_3min 现在接收并返回毫秒时间戳)
    aligned_ms_timestamp = align_time_to_3min(raw_ms_timestamp)

    # 将对齐时间转换为 datetime 用于日志 (可选)
    log_aligned_time = datetime.fromtimestamp(aligned_ms_timestamp / 1000, tz=timezone.utc)

    logging.info(
        f"准备保存数据... 对齐时间戳: {aligned_ms_timestamp} ({log_aligned_time.strftime('%Y-%m-%d %H:%M:%S %Z')})")

    expected_coins: Set[str] = set()
    values = []

    # 获取创建时间戳 (仅用于 created_at 字段，可以与 raw_ms_timestamp 相同)
    created_ms_timestamp = raw_ms_timestamp

    for coin in data:
        try:
            coin_id = coin.get('id')
            if not coin_id:
                logging.warning(f"跳过缺少 'id' 的币种: {coin.get('symbol')}")
                continue

            expected_coins.add(coin_id)

            last_updated_str = coin.get('last_updated')
            last_updated_ms = None
            if last_updated_str:
                # 关键步骤：解析原始的 UTC 时间字符串并转换为毫秒时间戳
                # 'Z' 替换为 '+00:00' 确保 fromisoformat 正确处理 UTC
                dt_obj = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
                # 转换为毫秒时间戳 (本质上是 UTC 毫秒时间戳)
                last_updated_ms = datetime_to_ms_timestamp(dt_obj)
            # 否则 last_updated_ms 保持 None

            row = (
                aligned_ms_timestamp,  # time (BIGINT)
                raw_ms_timestamp,  # raw_time (BIGINT)
                coin_id,
                coin.get('symbol'),
                coin.get('name'),
                coin.get('image'),
                coin.get('current_price'),
                coin.get('market_cap'),
                coin.get('market_cap_rank'),
                coin.get('fully_diluted_valuation'),
                coin.get('total_volume'),
                coin.get('circulating_supply'),
                coin.get('max_supply'),
                last_updated_ms,  # last_updated (BIGINT or NULL)
                created_ms_timestamp  # created_at (BIGINT)
            )
            values.append(row)
        except Exception as e:
            logging.error(f"处理币种数据时出错 {coin.get('id')}: {e}")

    if not values:
        logging.error("处理后没有有效数据可供保存")
        return False

    # 数据库字段 time, raw_time, last_updated, created_at 必须是 BIGINT
    insert_query = """
    INSERT INTO coin_data (
        time, raw_time, coin_id, symbol, name, image, current_price,
        market_cap, market_cap_rank, fully_diluted_valuation, total_volume,
        circulating_supply, max_supply,
        last_updated, created_at
    ) VALUES %s
    ON CONFLICT (time, coin_id) DO UPDATE SET
        raw_time = EXCLUDED.raw_time,
        symbol = EXCLUDED.symbol,
        name = EXCLUDED.name,
        image = EXCLUDED.image,
        current_price = EXCLUDED.current_price,
        market_cap = EXCLUDED.market_cap,
        market_cap_rank = EXCLUDED.market_cap_rank,
        fully_diluted_valuation = EXCLUDED.fully_diluted_valuation,
        total_volume = EXCLUDED.total_volume,
        circulating_supply = EXCLUDED.circulating_supply,
        max_supply = EXCLUDED.max_supply,
        last_updated = EXCLUDED.last_updated,
        created_at = EXCLUDED.created_at
    """

    try:
        with conn.cursor() as cur:
            execute_values(cur, insert_query, values)
        conn.commit()

        # 验证数据是否正确保存
        if not verify_database_save(conn, aligned_ms_timestamp, expected_coins):
            logging.error("数据库保存后验证失败")
            conn.rollback()  # 回滚事务
            return False

        logging.info(f"成功保存并验证 {len(values)} 条记录 (Rank: {values[0][8]} ...)")
        return True

    except Exception as e:
        logging.error(f"保存数据到数据库时出错: {e}")
        try:
            conn.rollback()
            logging.info("数据库事务已回滚")
        except Exception as rb_e:
            logging.error(f"回滚数据库事务时出错: {rb_e}")
        return False