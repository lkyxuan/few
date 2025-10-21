# config.py
import os
from dotenv import load_dotenv
from datetime import timezone, timedelta

# 加载 .env 文件中的环境变量
# 确保此文件在其他模块导入配置之前加载环境变量
load_dotenv()

# 数据库配置
DB_CONFIG = {
    'dbname': 'test',
    'host': 'localhost',
    'port': '5432',
    'user': 'postgres',
    "password": '2450512223'
}

# 时区配置
UTC_8 = timezone(timedelta(hours=8))

# CoinGecko API配置
COINGECKO_API_KEY = "CG-vC6ZXLLbamWGEFD1DJdGPnBW"
COINGECKO_API_URL = "https://pro-api.coingecko.com/api/v3"
COINS_PER_PAGE = 250
MAX_RETRIES = 3 # API请求最大重试次数
DB_CONNECT_RETRIES = 3 # 数据库连接重试次数

# Webhook 配置
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://open.larksuite.com/open-apis/bot/v2/hook/89ec58fd-27e4-43b0-b6dd-82c30e2a65da')

# 采集阈值
MIN_MARKET_CAP_THRESHOLD = 1000000 # 100万美元