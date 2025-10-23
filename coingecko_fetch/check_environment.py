import os
import sys
import psycopg2
import requests
import logging
from typing import List, Dict, Any

# 从配置模块导入常量
from config import DB_CONFIG, COINGECKO_API_KEY, COINGECKO_API_URL

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s'
)

def check_config():
    """检查配置是否正确"""
    try:
        # 检查数据库配置
        if not all(key in DB_CONFIG for key in ['dbname', 'host', 'port', 'user', 'password']):
            logging.error("数据库配置不完整")
            return False
            
        # 检查API配置
        if not COINGECKO_API_KEY:
            logging.warning("CoinGecko API 密钥未设置，将使用公共API（可能有限流）")
        else:
            logging.info("CoinGecko API 密钥已配置")
            
        logging.info("配置检查通过 ✓")
        return True
        
    except Exception as e:
        logging.error(f"配置检查失败: {e}")
        return False

def check_database():
    """检查数据库连接和表结构"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'coin_data'
                );
            """)
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logging.error("数据库表 'coin_data' 不存在")
                logging.error("请先创建必要的数据库表（参考 requirements.md）")
                return False
            
            # 检查表结构
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'coin_data';
            """)
            columns = cur.fetchall()
            
            required_columns = {
                'time': 'bigint',
                'raw_time': 'bigint',
                'coin_id': 'character varying',
                'symbol': 'character varying',
                'name': 'character varying',
                'current_price': 'numeric',
                'market_cap': 'numeric',
                'market_cap_rank': 'integer'
            }
            
            existing_columns = {col[0]: col[1] for col in columns}
            missing_columns = []
            
            for col, expected_type in required_columns.items():
                if col not in existing_columns:
                    missing_columns.append(col)
                elif not existing_columns[col].startswith(expected_type):
                    logging.warning(f"列 '{col}' 的类型可能不正确: 期望 {expected_type}, 实际 {existing_columns[col]}")
                    # 对于 bigint 类型，检查是否包含 bigint
                    if expected_type == 'bigint' and 'bigint' not in existing_columns[col]:
                        logging.error(f"列 '{col}' 必须是 BIGINT 类型")
                        return False
            
            if missing_columns:
                logging.error(f"缺少以下列: {', '.join(missing_columns)}")
                return False
                
        conn.close()
        logging.info("数据库检查通过 ✓")
        return True
        
    except Exception as e:
        logging.error(f"数据库连接失败: {e}")
        return False

def check_api():
    """检查 CoinGecko API 是否可用"""
    try:
        headers = {'Accept': 'application/json'}
        if COINGECKO_API_KEY:
            headers['x-cg-pro-api-key'] = COINGECKO_API_KEY
            
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/markets",
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 1,
                'page': 1,
                'sparkline': 'false'
            },
            headers=headers,
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list) or not data:
            logging.error("API 返回数据格式不正确")
            return False
            
        # 检查返回的数据是否包含必要字段
        coin = data[0]
        required_fields = ['id', 'symbol', 'name', 'current_price', 'market_cap']
        missing_fields = [field for field in required_fields if field not in coin]
        
        if missing_fields:
            logging.warning(f"API 返回数据缺少字段: {', '.join(missing_fields)}")
            
        logging.info("API 检查通过 ✓")
        return True
        
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求失败: {e}")
        return False

def check_timescaledb():
    """检查 TimescaleDB 扩展是否可用"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor() as cur:
            # 检查 TimescaleDB 扩展是否存在
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                );
            """)
            timescaledb_exists = cur.fetchone()[0]
            
            if not timescaledb_exists:
                logging.warning("TimescaleDB 扩展未安装，将使用标准 PostgreSQL 表")
                return True  # 不是致命错误，只是警告
            
            # 检查超表是否存在
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM timescaledb_information.hypertables 
                    WHERE hypertable_name = 'coin_data'
                );
            """)
            hypertable_exists = cur.fetchone()[0]
            
            if hypertable_exists:
                logging.info("TimescaleDB 超表检查通过 ✓")
            else:
                logging.warning("coin_data 表未转换为超表，建议运行 init_timescaledb.py")
                
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"TimescaleDB 检查失败: {e}")
        return False


def main():
    """主函数"""
    logging.info("开始环境检查...")
    
    checks = [
        ("配置", check_config),
        ("数据库", check_database),
        ("TimescaleDB", check_timescaledb),
        ("API", check_api)
    ]
    
    all_passed = True
    
    for name, check in checks:
        logging.info(f"\n检查 {name}...")
        if not check():
            all_passed = False
    
    if all_passed:
        logging.info("\n✅ 所有检查都通过了！可以运行 main.py 开始采集数据")
    else:
        logging.error("\n❌ 环境检查失败，请解决上述问题后再运行采集程序")
        sys.exit(1)

if __name__ == "__main__":
    main() 