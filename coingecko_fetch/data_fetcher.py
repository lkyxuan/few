# data_fetcher.py
import requests
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

# 从配置模块导入常量
from config import (
    COINGECKO_API_KEY, COINGECKO_API_URL,
    COINS_PER_PAGE, MAX_RETRIES, MIN_MARKET_CAP_THRESHOLD
)


def validate_coin_data(coin: Dict[str, Any]) -> bool:
    """验证单个币种数据的完整性"""
    required_fields = ['id', 'symbol', 'name', 'market_cap_rank']
    if not all(coin.get(field) is not None for field in required_fields):
        logging.warning(f"币种数据不完整，缺少必填字段: {coin.get('id', 'N/A')}")
        return False
    return True


def fetch_coin_data(page: int, retries: int = 0) -> Optional[List[Dict[Any, Any]]]:
    """从CoinGecko获取币种数据，支持重试"""
    if retries >= MAX_RETRIES:
        logging.error(f"获取第 {page} 页数据失败，已达到最大重试次数")
        return None

    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': COINS_PER_PAGE,
        'page': page,
        'sparkline': 'false',
        'price_change_percentage': '24h,7d,30d',
    }

    headers = {
        'Accept': 'application/json'
    }

    # 仅在 API Key 存在时才添加
    if COINGECKO_API_KEY:
        # 根据 CoinGecko Pro API 文档，Key 应该在 Header 中
        headers['x-cg-pro-api-key'] = COINGECKO_API_KEY
    else:
        # 如果使用公共API，URL可能不同
        logging.warning("COINGECKO_API_KEY 未设置，将使用公共API (可能有限流)")
        # 公共API URL (如果与Pro不同)
        # public_api_url = "https://api.coingecko.com/api/v3"
        # current_url = public_api_url
        # (保持原URL，Pro的URL在没有key时也能工作，但会受限)
        current_url = COINGECKO_API_URL.replace("pro-", "")  # 尝试使用公共API端点

    current_url = f"{COINGECKO_API_URL}/coins/markets"

    try:
        logging.info(f"正在获取第 {page} 页数据（第 {retries + 1} 次尝试）...")
        response = requests.get(
            current_url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()  # 如果状态码不是 2xx，则引发异常

        data = response.json()

        if not isinstance(data, list):
            logging.error(f"API返回的数据格式不正确: {type(data)}。预期是列表。")
            raise ValueError("API返回的数据格式不正确，预期是列表")

        if not data and page > 1:
            logging.info(f"第 {page} 页返回空数据，可能是最后一页。")
            return []  # 返回空列表表示结束

        # 验证每个币种的数据完整性
        valid_data = [coin for coin in data if validate_coin_data(coin)]
        invalid_count = len(data) - len(valid_data)

        if invalid_count > 0:
            logging.warning(f"第 {page} 页有 {invalid_count} 个币种数据不完整，已过滤")

        if not valid_data and data:
            logging.error(f"第 {page} 页所有数据均无效")
            raise ValueError("没有有效的币种数据")

        return valid_data

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"API HTTP错误 (page {page}, 尝试 {retries + 1}): {http_err} - {response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        logging.error(f"API 连接错误 (page {page}, 尝试 {retries + 1}): {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        logging.error(f"API 请求超时 (page {page}, 尝试 {retries + 1}): {timeout_err}")
    except Exception as e:
        logging.error(f"API 请求失败 (page {page}, 尝试 {retries + 1}): {e}")

    # 如果发生异常，进行指数退避重试
    time.sleep(2 ** retries)
    return fetch_coin_data(page, retries + 1)


# data = fetch_coin_data(1)  # 测试调用，实际使用时可移除
# print(data)



def verify_batch_data(data: List[Dict[Any, Any]], expected_range: Tuple[int, int]) -> Tuple[bool, bool]:
    """
    验证批次数据的完整性。
    返回 (is_valid, should_stop)
    is_valid: 当前批次是否有效
    should_stop: 是否应停止采集 (例如市值过低)
    """
    if not data:
        logging.error("数据验证失败：数据为空")
        return False, False  # 数据无效，但不一定停止

    # 检查市值排名
    ranks = [coin.get('market_cap_rank', 0) for coin in data if coin.get('market_cap_rank')]
    if not ranks:
        logging.error("数据验证失败：没有有效的市值排名数据")
        return False, False

    # 检查最小市值
    market_caps = [coin.get('market_cap', 0) for coin in data if coin.get('market_cap') is not None]
    min_market_cap = 0
    if market_caps:
        min_market_cap = min(market_caps)
        logging.info(f"当前批次市值范围: ${min(market_caps):,.2f} - ${max(market_caps):,.2f}")
        if min_market_cap < MIN_MARKET_CAP_THRESHOLD:
            logging.info(
                f"检测到市值低于 ${MIN_MARKET_CAP_THRESHOLD:,.0f} 的币种 (最小: ${min_market_cap:,.2f})，本轮采集完成")
            return True, True  # 数据有效，但应停止

    # min_rank, max_rank = min(ranks), max(ranks)
    # expected_min = expected_range[0]
    # expected_max = expected_range[1]
    # rank_tolerance = 50  # 允许排名有 50 的浮动范围
    #
    # # 检查排名是否在预期范围内 (允许浮动)
    # if not (expected_min - rank_tolerance <= min_rank <= expected_min + rank_tolerance):
    #     logging.warning(
    #         f"市值排名范围与预期有偏差: 实际最小Rank {min_rank}, 预期 {expected_min} (容差 {rank_tolerance})"
    #     )
    #     # 即使有偏差，也可能继续，但这可能表示API数据有跳跃
    #
    # logging.info(f"数据验证: 实际排名 {min_rank}-{max_rank}, 预期 {expected_min}-{expected_max}")
    return True, False