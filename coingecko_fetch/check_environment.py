import os
import sys
from dotenv import load_dotenv
import psycopg2
import requests
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_env_variables():
    """检查环境变量是否配置正确"""
    load_dotenv()
    
    required_vars = [
        'DB_NAME',
        'DB_USER',
        'DB_PASSWORD',
        'DB_HOST',
        'DB_PORT',
        'COINGECKO_API_KEY'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"缺少以下环境变量: {', '.join(missing_vars)}")
        logging.error("请创建 .env 文件并设置正确的环境变量")
        return False
        
    logging.info("环境变量检查通过 ✓")
    return True

def check_database():
    """检查数据库连接和表结构"""
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        
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
                'time': 'timestamp with time zone',
                'raw_time': 'timestamp with time zone',
                'coin_id': 'character varying',
                'symbol': 'character varying',
                'name': 'character varying'
            }
            
            existing_columns = {col[0]: col[1] for col in columns}
            missing_columns = []
            
            for col, type_ in required_columns.items():
                if col not in existing_columns:
                    missing_columns.append(col)
                elif not existing_columns[col].startswith(type_):
                    logging.error(f"列 '{col}' 的类型不正确: 期望 {type_}, 实际 {existing_columns[col]}")
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
        api_key = os.getenv('COINGECKO_API_KEY')
        response = requests.get(
            "https://pro-api.coingecko.com/api/v3/coins/markets",
            params={
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 1,
                'page': 1,
                'sparkline': 'false',
                'x_cg_pro_api_key': api_key
            },
            timeout=10
        )
        
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list) or not data:
            logging.error("API 返回数据格式不正确")
            return False
            
        logging.info("API 检查通过 ✓")
        return True
        
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求失败: {e}")
        return False

def main():
    """主函数"""
    logging.info("开始环境检查...")
    
    checks = [
        ("环境变量", check_env_variables),
        ("数据库", check_database),
        ("API", check_api)
    ]
    
    all_passed = True
    
    for name, check in checks:
        logging.info(f"\n检查 {name}...")
        if not check():
            all_passed = False
    
    if all_passed:
        logging.info("\n✅ 所有检查都通过了！可以运行 coingecko_collector.py 开始采集数据")
    else:
        logging.error("\n❌ 环境检查失败，请解决上述问题后再运行采集程序")
        sys.exit(1)

if __name__ == "__main__":
    main() 