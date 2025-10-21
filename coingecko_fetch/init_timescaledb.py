import os
import sys
from dotenv import load_dotenv
import psycopg2
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# def create_database():
#     """创建 TimescaleDB 数据库"""
#     load_dotenv()
#
#     # 连接到默认的 postgres 数据库来创建新数据库
#     conn = psycopg2.connect(
#         dbname='postgres',
#         user=os.getenv('DB_USER'),
#         password=os.getenv('DB_PASSWORD'),
#         host=os.getenv('DB_HOST'),
#         port=os.getenv('DB_PORT')
#     )
#     conn.autocommit = True
#
#     try:
#         with conn.cursor() as cur:
#             # 检查数据库是否已存在
#             cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{os.getenv('DB_NAME')}'")
#             exists = cur.fetchone()
#
#             if not exists:
#                 # 创建数据库
#                 cur.execute(f"CREATE DATABASE {os.getenv('DB_NAME')}")
#                 logging.info(f"数据库 '{os.getenv('DB_NAME')}' 创建成功")
#             else:
#                 logging.info(f"数据库 '{os.getenv('DB_NAME')}' 已存在")
#     finally:
#         conn.close()

def init_timescaledb():
    """使用Unix时间戳（毫秒）初始化TimescaleDB表结构。"""
    conn = None  # 将 conn 初始化为 None
    try:
        # 使用环境变量中的连接信息，或者回退到默认值
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'test'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '2450512223')
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            # 启用TimescaleDB扩展
            logging.info("正在启用 TimescaleDB 扩展...")
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")

            # 创建主数据表，时间列使用BIGINT类型存储毫秒时间戳
            logging.info("正在创建 'coin_data' 表...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS coin_data (
                    time BIGINT NOT NULL,                  -- Unix时间戳（毫秒），已对齐到3分钟，主键之一
                    raw_time BIGINT,                       -- 原始采集的Unix时间戳（毫秒）
                    coin_id VARCHAR(255) NOT NULL,         -- 代币ID，主键之一
                    symbol VARCHAR(255),                   -- 代币符号
                    name VARCHAR(255),                     -- 代币名称
                    image TEXT,                            -- 代币图片URL
                    current_price DECIMAL(40, 18),         -- 当前价格（提高精度）
                    market_cap DECIMAL(40, 8),             -- 市值
                    market_cap_rank INTEGER,               -- 市值排名
                    fully_diluted_valuation DECIMAL(40, 8),-- 完全稀释估值
                    total_volume DECIMAL(40, 8),           -- 24小时总交易量
                    circulating_supply DECIMAL(40, 8),     -- 流通供应量
                    max_supply DECIMAL(40, 8),             -- 最大供应量
                    last_updated BIGINT,                   -- API数据最后更新时间戳（毫秒）
                    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT, -- 数据行创建时间戳（毫秒）
                    PRIMARY KEY (time, coin_id)
                );
            """)

            # 将表转换为超表 (hypertable)
            logging.info("正在将 'coin_data' 转换为超表...")
            cur.execute("""
                SELECT create_hypertable('coin_data', 'time',
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
            """)

            # 创建索引以提高查询性能
            logging.info("正在创建索引...")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_coin_data_coin_id ON coin_data(coin_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_coin_data_time_desc ON coin_data(time DESC);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_coin_data_market_cap_rank ON coin_data(market_cap_rank);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_coin_data_raw_time ON coin_data(raw_time);")

            logging.info("TimescaleDB 表结构初始化成功。")

            # 创建或替换有用的视图，使用epoch时间（毫秒）进行过滤
            logging.info("正在创建/更新数据库视图...")
            cur.execute("""
                -- 视图：获取过去10分钟内每个代币的最新数据
                CREATE OR REPLACE VIEW latest_prices AS
                SELECT DISTINCT ON (coin_id)
                    coin_id,
                    name,
                    symbol,
                    current_price,
                    market_cap_rank,
                    time
                FROM coin_data
                -- 筛选过去10分钟（600,000毫秒）内的数据
                WHERE time >= (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 600000
                ORDER BY coin_id, time DESC;
            """)

            cur.execute("""
                -- 视图：计算24小时价格和市值的变化
                CREATE OR REPLACE VIEW price_changes_24h AS
                WITH latest AS (
                    -- 获取每个代币最新的数据点
                    SELECT DISTINCT ON (coin_id)
                        coin_id,
                        current_price,
                        market_cap,
                        time
                    FROM coin_data
                    -- 在最近的时间窗口内搜索以提高性能
                    WHERE time >= (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 600000
                    ORDER BY coin_id, time DESC
                ),
                day_ago AS (
                    -- 获取大约24小时前的数据点
                    SELECT DISTINCT ON (coin_id)
                        coin_id,
                        current_price as price_24h_ago,
                        market_cap as market_cap_24h_ago,
                        time
                    FROM coin_data
                    -- 在24小时标记附近的时间窗口内查找（例如，23小时55分钟前到24小时5分钟前）
                    WHERE time BETWEEN ((EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 86700000) AND ((EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 86100000)
                    ORDER BY coin_id, time DESC
                )
                SELECT
                    l.coin_id,
                    l.current_price,
                    d.price_24h_ago,
                    -- 防止除以零
                    CASE
                        WHEN d.price_24h_ago > 0 THEN ((l.current_price - d.price_24h_ago) / d.price_24h_ago * 100)
                        ELSE 0
                    END as price_change_percentage,
                    l.market_cap,
                    d.market_cap_24h_ago,
                    CASE
                        WHEN d.market_cap_24h_ago > 0 THEN ((l.market_cap - d.market_cap_24h_ago) / d.market_cap_24h_ago * 100)
                        ELSE 0
                    END as market_cap_change_percentage
                FROM latest l
                JOIN day_ago d ON l.coin_id = d.coin_id;
            """)

            logging.info("数据库视图创建/更新成功。")

    except psycopg2.Error as e:
        logging.error(f"初始化过程中发生数据库错误: {e}")
        raise
    except Exception as e:
        logging.error(f"初始化过程中发生未知错误: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logging.info("数据库连接已关闭。")

def main():
    """主执行函数。"""
    try:
        logging.info("开始初始化 TimescaleDB...")

        # 步骤1：如果数据库不存在，则创建它（可选）
        # create_database()

        # 步骤2：初始化表、超表、索引和视图
        init_timescaledb()

        logging.info("\n✅ TimescaleDB 初始化完成！")
        logging.info("现在可以运行你的数据采集脚本了。")

    except Exception:
        # 具体的错误已在上面的函数中记录
        logging.error("\n❌ 初始化失败。请查看日志以获取详细信息。")
        sys.exit(1)

if __name__ == "__main__":
    main()