from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, text, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import math
import os
from pathlib import Path

from models.coin import (
    CoinData, HistoricalData, MarketStats, Pagination, 
    CoinListResponse, CoinHistoryResponse, TrendingCoinsResponse
)

logger = logging.getLogger(__name__)


class CoinService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_dir = Path("/databao/dataview/backend/static/coin-images")

    def _get_local_image_url(self, coin_id: str, original_url: str = None) -> str:
        """获取本地图片URL，如果不存在则返回图片API URL"""
        if not coin_id:
            return "/api/v1/images/coin/placeholder"

        # 检查常见的图片扩展名
        extensions = ['.png', '.jpg', '.jpeg', '.webp', '.svg']

        for ext in extensions:
            local_path = self.cache_dir / f"{coin_id}{ext}"
            if local_path.exists():
                return f"/api/v1/images/coin/{coin_id}"

        # 如果本地没有缓存，返回图片API URL，让它处理下载
        if original_url:
            return f"/api/v1/images/coin/{coin_id}?url={original_url}"
        else:
            return f"/api/v1/images/coin/{coin_id}"
    
    async def get_coins(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        sort: str = "market_cap_rank",
        order: str = "asc"
    ) -> CoinListResponse:
        """获取币种列表（包含指标数据）"""
        try:
            # 构建基础查询 - 使用子查询获取每个币种的最新数据和指标数据
            # 如果有搜索条件，将其提前应用以提高性能
            search_condition = ""
            if search:
                search_condition = " AND (LOWER(coin_id) LIKE :search OR LOWER(symbol) LIKE :search OR LOWER(name) LIKE :search)"

            base_query = f"""
            WITH latest_coin_data AS (
                SELECT coin_id, symbol, name, image,
                       current_price, market_cap, market_cap_rank,
                       fully_diluted_valuation, total_volume,
                       circulating_supply, max_supply,
                       price_change_24h, price_change_percentage_24h,
                       market_cap_change_24h, market_cap_change_percentage_24h,
                       ath, ath_change_percentage, ath_date,
                       atl, atl_change_percentage, atl_date,
                       last_updated, time,
                       ROW_NUMBER() OVER (PARTITION BY coin_id ORDER BY time DESC) as rn
                FROM coin_data
                WHERE time >= NOW() - INTERVAL '1 day'{search_condition}
            ),
            coin_with_indicators AS (
                SELECT c.coin_id, c.symbol, c.name, c.image,
                       c.current_price, c.market_cap, c.market_cap_rank,
                       c.fully_diluted_valuation, c.total_volume,
                       c.circulating_supply, c.max_supply,
                       c.price_change_24h, c.price_change_percentage_24h,
                       c.market_cap_change_24h, c.market_cap_change_percentage_24h,
                       c.ath, c.ath_change_percentage, c.ath_date,
                       c.atl, c.atl_change_percentage, c.atl_date,
                       c.last_updated, c.time,
                       -- 指标数据
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_1H' THEN i.indicator_value END) as volume_change_1h,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_3H' THEN i.indicator_value END) as volume_change_3h,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_24H' THEN i.indicator_value END) as volume_change_24h,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_8H' THEN i.indicator_value END) as volume_change_8h,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_3M' THEN i.indicator_value END) as volume_change_3m,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_6M' THEN i.indicator_value END) as volume_change_6m,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_9M' THEN i.indicator_value END) as volume_change_9m,
                       MAX(CASE WHEN i.indicator_name = 'PRICE_CHANGE_3M' THEN i.indicator_value END) as price_change_3m,
                       MAX(CASE WHEN i.indicator_name = 'PRICE_CHANGE_6M' THEN i.indicator_value END) as price_change_6m,
                       MAX(CASE WHEN i.indicator_name = 'PRICE_CHANGE_12M' THEN i.indicator_value END) as price_change_12m,
                       MAX(CASE WHEN i.indicator_name = 'AVG_BTC_ETH' THEN i.indicator_value END) as avg_btc_eth,
                       MAX(CASE WHEN i.indicator_name = 'AVG_BTC_ETH_SOL' THEN i.indicator_value END) as avg_btc_eth_sol,
                       MAX(CASE WHEN i.indicator_name = 'WEIGHTED_AVG_BTC_ETH' THEN i.indicator_value END) as weighted_avg_btc_eth,
                       MAX(CASE WHEN i.indicator_name = 'WEIGHTED_AVG_BTC_ETH_SOL' THEN i.indicator_value END) as weighted_avg_btc_eth_sol,
                       MAX(CASE WHEN i.indicator_name = 'WEIGHTED_AVG_SOL_ETH_BNB' THEN i.indicator_value END) as weighted_avg_sol_eth_bnb,
                       -- 三个核心自定义指标
                       MAX(CASE WHEN i.indicator_name = 'CAPITAL_INFLOW_INTENSITY_3M' THEN i.indicator_value END) as capital_inflow_intensity_3m,
                       MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_RATIO_3M' THEN i.indicator_value END) as volume_change_ratio_3m,
                       MAX(CASE WHEN i.indicator_name = 'AVG_VOLUME_3M_24H' THEN i.indicator_value END) as avg_volume_3m_24h
                FROM latest_coin_data c
                LEFT JOIN indicator_data i ON c.coin_id = i.coin_id AND c.time = i.time
                WHERE c.rn = 1
                GROUP BY c.coin_id, c.symbol, c.name, c.image, c.current_price, c.market_cap, c.market_cap_rank,
                         c.fully_diluted_valuation, c.total_volume, c.circulating_supply, c.max_supply,
                         c.price_change_24h, c.price_change_percentage_24h, c.market_cap_change_24h, c.market_cap_change_percentage_24h,
                         c.ath, c.ath_change_percentage, c.ath_date, c.atl, c.atl_change_percentage, c.atl_date, c.last_updated, c.time
            )
            SELECT coin_id, symbol, name, image,
                   current_price, market_cap, market_cap_rank,
                   fully_diluted_valuation, total_volume,
                   circulating_supply, max_supply,
                   price_change_24h, price_change_percentage_24h,
                   market_cap_change_24h, market_cap_change_percentage_24h,
                   ath, ath_change_percentage, ath_date,
                   atl, atl_change_percentage, atl_date,
                   last_updated, time,
                   volume_change_1h, volume_change_3h, volume_change_24h, volume_change_8h,
                   volume_change_3m, volume_change_6m, volume_change_9m,
                   price_change_3m, price_change_6m, price_change_12m,
                   avg_btc_eth, avg_btc_eth_sol, weighted_avg_btc_eth,
                   weighted_avg_btc_eth_sol, weighted_avg_sol_eth_bnb,
                   capital_inflow_intensity_3m, volume_change_ratio_3m, avg_volume_3m_24h
            FROM coin_with_indicators
            """
            
            params = {}

            # 设置搜索参数
            if search:
                params['search'] = f"%{search.lower()}%"
            
            # 排序 - 支持基础字段和指标字段
            allowed_sort_fields = [
                'market_cap_rank', 'current_price', 'market_cap', 'total_volume', 'price_change_percentage_24h',
                'volume_change_1h', 'volume_change_3h', 'volume_change_24h', 'volume_change_8h',
                'volume_change_3m', 'volume_change_6m', 'volume_change_9m',
                'price_change_3m', 'price_change_6m', 'price_change_12m',
                # 核心自定义指标
                'capital_inflow_intensity_3m', 'volume_change_ratio_3m', 'avg_volume_3m_24h'
            ]
            
            if sort in allowed_sort_fields:
                if order.lower() == 'desc':
                    query = base_query + f" ORDER BY {sort} DESC NULLS LAST"
                else:
                    query = base_query + f" ORDER BY {sort} ASC NULLS LAST"
            else:
                query = base_query + " ORDER BY market_cap_rank ASC NULLS LAST"
            
            # 计算总数
            count_query = f"""
            SELECT COUNT(DISTINCT coin_id) as total
            FROM coin_data
            WHERE time >= NOW() - INTERVAL '1 day'
            """
            
            if search:
                count_query += " AND (LOWER(name) LIKE :search OR LOWER(symbol) LIKE :search OR LOWER(coin_id) LIKE :search)"
            
            # 执行计数查询
            count_result = await self.db.execute(text(count_query), params)
            total = count_result.scalar() or 0
            
            # 计算分页
            total_pages = math.ceil(total / limit) if total > 0 else 0
            offset = (page - 1) * limit
            
            # 添加分页
            query += f" LIMIT {limit} OFFSET {offset}"
            
            # 执行主查询
            result = await self.db.execute(text(query), params)
            rows = result.fetchall()
            
            # 转换为 Pydantic 模型
            coins = []
            for row in rows:
                coin_data = {
                    'coin_id': row.coin_id,
                    'symbol': row.symbol,
                    'name': row.name,
                    'image': self._get_local_image_url(row.coin_id, row.image),
                    'current_price': float(row.current_price) if row.current_price else None,
                    'market_cap': float(row.market_cap) if row.market_cap else None,
                    'market_cap_rank': row.market_cap_rank,
                    'fully_diluted_valuation': float(row.fully_diluted_valuation) if row.fully_diluted_valuation else None,
                    'total_volume': float(row.total_volume) if row.total_volume else None,
                    'circulating_supply': float(row.circulating_supply) if row.circulating_supply else None,
                    'max_supply': float(row.max_supply) if row.max_supply else None,
                    'price_change_24h': float(row.price_change_24h) if row.price_change_24h else None,
                    'price_change_percentage_24h': float(row.price_change_percentage_24h) if row.price_change_percentage_24h else None,
                    'market_cap_change_24h': float(row.market_cap_change_24h) if row.market_cap_change_24h else None,
                    'market_cap_change_percentage_24h': float(row.market_cap_change_percentage_24h) if row.market_cap_change_percentage_24h else None,
                    'ath': float(row.ath) if row.ath else None,
                    'ath_change_percentage': float(row.ath_change_percentage) if row.ath_change_percentage else None,
                    'ath_date': row.ath_date,
                    'atl': float(row.atl) if row.atl else None,
                    'atl_change_percentage': float(row.atl_change_percentage) if row.atl_change_percentage else None,
                    'atl_date': row.atl_date,
                    'last_updated': row.last_updated,
                    'time': row.time,
                    # 指标数据
                    'volume_change_1h': float(row.volume_change_1h) if row.volume_change_1h is not None else None,
                    'volume_change_3h': float(row.volume_change_3h) if row.volume_change_3h is not None else None,
                    'volume_change_24h': float(row.volume_change_24h) if row.volume_change_24h is not None else None,
                    'volume_change_8h': float(row.volume_change_8h) if row.volume_change_8h is not None else None,
                    'volume_change_3m': float(row.volume_change_3m) if row.volume_change_3m is not None else None,
                    'volume_change_6m': float(row.volume_change_6m) if row.volume_change_6m is not None else None,
                    'volume_change_9m': float(row.volume_change_9m) if row.volume_change_9m is not None else None,
                    'price_change_3m': float(row.price_change_3m) if row.price_change_3m is not None else None,
                    'price_change_6m': float(row.price_change_6m) if row.price_change_6m is not None else None,
                    'price_change_12m': float(row.price_change_12m) if row.price_change_12m is not None else None,
                    'avg_btc_eth': float(row.avg_btc_eth) if row.avg_btc_eth is not None else None,
                    'avg_btc_eth_sol': float(row.avg_btc_eth_sol) if row.avg_btc_eth_sol is not None else None,
                    'weighted_avg_btc_eth': float(row.weighted_avg_btc_eth) if row.weighted_avg_btc_eth is not None else None,
                    'weighted_avg_btc_eth_sol': float(row.weighted_avg_btc_eth_sol) if row.weighted_avg_btc_eth_sol is not None else None,
                    'weighted_avg_sol_eth_bnb': float(row.weighted_avg_sol_eth_bnb) if row.weighted_avg_sol_eth_bnb is not None else None,
                    # 三个核心自定义指标
                    'capital_inflow_intensity_3m': float(row.capital_inflow_intensity_3m) if row.capital_inflow_intensity_3m is not None else None,
                    'volume_change_ratio_3m': float(row.volume_change_ratio_3m) if row.volume_change_ratio_3m is not None else None,
                    'avg_volume_3m_24h': float(row.avg_volume_3m_24h) if row.avg_volume_3m_24h is not None else None,
                }
                coins.append(CoinData(**coin_data))
            
            # 构建分页信息
            pagination = Pagination(
                page=page,
                limit=limit,
                total=total,
                total_pages=total_pages
            )
            
            # 获取市场统计（可选）
            market_stats = await self.get_market_stats()
            
            return CoinListResponse(
                data=coins,
                pagination=pagination,
                meta=market_stats
            )
            
        except Exception as e:
            logger.error(f"Error getting coins: {e}")
            raise
    
    async def get_coin(self, coin_id: str) -> Optional[CoinData]:
        """获取单个币种详情（包含指标数据）"""
        try:
            # 获取基础币种数据
            coin_query = """
            SELECT coin_id, symbol, name, image,
                   current_price, market_cap, market_cap_rank,
                   fully_diluted_valuation, total_volume,
                   circulating_supply, max_supply,
                   price_change_24h, price_change_percentage_24h,
                   market_cap_change_24h, market_cap_change_percentage_24h,
                   ath, ath_change_percentage, ath_date,
                   atl, atl_change_percentage, atl_date,
                   last_updated, time
            FROM coin_data
            WHERE coin_id = :coin_id
            ORDER BY time DESC
            LIMIT 1
            """
            
            coin_result = await self.db.execute(text(coin_query), {'coin_id': coin_id})
            coin_row = coin_result.fetchone()
            
            if not coin_row:
                return None
            
            # 获取指标数据 - 基于币种数据的时间获取对应的指标
            indicators_query = """
            SELECT indicator_name, indicator_value
            FROM indicator_data
            WHERE coin_id = :coin_id
              AND time = :time
              AND indicator_name IN (
                  'VOLUME_CHANGE_1H', 'VOLUME_CHANGE_3H', 'VOLUME_CHANGE_24H',
                  'VOLUME_CHANGE_8H', 'VOLUME_CHANGE_3M', 'VOLUME_CHANGE_6M', 'VOLUME_CHANGE_9M',
                  'PRICE_CHANGE_3M', 'PRICE_CHANGE_6M', 'PRICE_CHANGE_12M',
                  'AVG_BTC_ETH', 'AVG_BTC_ETH_SOL', 'WEIGHTED_AVG_BTC_ETH',
                  'WEIGHTED_AVG_BTC_ETH_SOL', 'WEIGHTED_AVG_SOL_ETH_BNB'
              )
            """
            
            indicators_result = await self.db.execute(text(indicators_query), {
                'coin_id': coin_id, 
                'time': coin_row.time
            })
            indicators_rows = indicators_result.fetchall()
            
            # 将指标数据转换为字典
            indicators = {}
            for ind_row in indicators_rows:
                # 转换指标名称为模型字段名
                field_map = {
                    'VOLUME_CHANGE_1H': 'volume_change_1h',
                    'VOLUME_CHANGE_3H': 'volume_change_3h',
                    'VOLUME_CHANGE_24H': 'volume_change_24h',
                    'VOLUME_CHANGE_8H': 'volume_change_8h',
                    'VOLUME_CHANGE_3M': 'volume_change_3m',
                    'VOLUME_CHANGE_6M': 'volume_change_6m',
                    'VOLUME_CHANGE_9M': 'volume_change_9m',
                    'PRICE_CHANGE_3M': 'price_change_3m',
                    'PRICE_CHANGE_6M': 'price_change_6m',
                    'PRICE_CHANGE_12M': 'price_change_12m',
                    'AVG_BTC_ETH': 'avg_btc_eth',
                    'AVG_BTC_ETH_SOL': 'avg_btc_eth_sol',
                    'WEIGHTED_AVG_BTC_ETH': 'weighted_avg_btc_eth',
                    'WEIGHTED_AVG_BTC_ETH_SOL': 'weighted_avg_btc_eth_sol',
                    'WEIGHTED_AVG_SOL_ETH_BNB': 'weighted_avg_sol_eth_bnb'
                }
                
                field_name = field_map.get(ind_row.indicator_name)
                if field_name:
                    indicators[field_name] = float(ind_row.indicator_value) if ind_row.indicator_value else None
            
            # 构建币种数据
            coin_data = {
                'coin_id': coin_row.coin_id,
                'symbol': coin_row.symbol,
                'name': coin_row.name,
                'image': coin_row.image,
                'current_price': float(coin_row.current_price) if coin_row.current_price else None,
                'market_cap': float(coin_row.market_cap) if coin_row.market_cap else None,
                'market_cap_rank': coin_row.market_cap_rank,
                'fully_diluted_valuation': float(coin_row.fully_diluted_valuation) if coin_row.fully_diluted_valuation else None,
                'total_volume': float(coin_row.total_volume) if coin_row.total_volume else None,
                'circulating_supply': float(coin_row.circulating_supply) if coin_row.circulating_supply else None,
                'max_supply': float(coin_row.max_supply) if coin_row.max_supply else None,
                'price_change_24h': float(coin_row.price_change_24h) if coin_row.price_change_24h else None,
                'price_change_percentage_24h': float(coin_row.price_change_percentage_24h) if coin_row.price_change_percentage_24h else None,
                'market_cap_change_24h': float(coin_row.market_cap_change_24h) if coin_row.market_cap_change_24h else None,
                'market_cap_change_percentage_24h': float(coin_row.market_cap_change_percentage_24h) if coin_row.market_cap_change_percentage_24h else None,
                'ath': float(coin_row.ath) if coin_row.ath else None,
                'ath_change_percentage': float(coin_row.ath_change_percentage) if coin_row.ath_change_percentage else None,
                'ath_date': coin_row.ath_date,
                'atl': float(coin_row.atl) if coin_row.atl else None,
                'atl_change_percentage': float(coin_row.atl_change_percentage) if coin_row.atl_change_percentage else None,
                'atl_date': coin_row.atl_date,
                'last_updated': coin_row.last_updated,
                **indicators  # 添加所有指标数据
            }
            
            return CoinData(**coin_data)
            
        except Exception as e:
            logger.error(f"Error getting coin {coin_id}: {e}")
            raise
    
    async def get_coin_history(
        self,
        coin_id: str,
        start: datetime,
        end: datetime,
        interval: str = "1h"
    ) -> CoinHistoryResponse:
        """获取币种历史数据 - 使用TimescaleDB优化查询"""
        try:
            # 构建时间间隔的 SQL - TimescaleDB支持
            interval_map = {
                "1m": "1 minute",
                "5m": "5 minutes",
                "15m": "15 minutes",
                "1h": "1 hour",
                "4h": "4 hours",
                "1d": "1 day",
                "1w": "1 week"
            }

            sql_interval = interval_map.get(interval, "1 hour")

            # 使用TimescaleDB的time_bucket函数进行高效时间聚合
            query = f"""
            WITH time_series AS (
                SELECT time_bucket('{sql_interval}', time) AS bucket_time,
                       first(current_price, time) AS open,
                       max(current_price) AS high,
                       min(current_price) AS low,
                       last(current_price, time) AS close,
                       avg(total_volume) AS volume
                FROM coin_data
                WHERE coin_id = :coin_id
                  AND time >= :start
                  AND time <= :end
                  AND current_price IS NOT NULL
                GROUP BY bucket_time
                ORDER BY bucket_time
            )
            SELECT bucket_time as time, open, high, low, close, volume
            FROM time_series
            """
            
            result = await self.db.execute(text(query), {
                'coin_id': coin_id,
                'start': start,
                'end': end
            })
            
            historical_data = []
            for row in result:
                data = {
                    'time': row.time,
                    'open': float(row.open) if row.open else None,
                    'high': float(row.high) if row.high else None,
                    'low': float(row.low) if row.low else None,
                    'close': float(row.close) if row.close else None,
                    'volume': float(row.volume) if row.volume else None
                }
                historical_data.append(HistoricalData(**data))
            
            return CoinHistoryResponse(
                coin_id=coin_id,
                interval=interval,
                data=historical_data
            )
            
        except Exception as e:
            logger.error(f"Error getting coin history for {coin_id}: {e}")
            raise
    
    async def get_market_stats(self) -> MarketStats:
        """获取市场统计数据"""
        try:
            # 获取最新的市场数据
            query = """
            WITH latest_data AS (
                SELECT DISTINCT ON (coin_id)
                    coin_id, current_price, market_cap, total_volume,
                    market_cap_change_percentage_24h, last_updated
                FROM coin_data
                WHERE time >= NOW() - INTERVAL '1 day'
                  AND current_price IS NOT NULL
                  AND market_cap IS NOT NULL
                ORDER BY coin_id, time DESC
            )
            SELECT 
                SUM(market_cap) AS total_market_cap,
                SUM(total_volume) AS total_volume_24h,
                AVG(market_cap_change_percentage_24h) AS avg_market_cap_change,
                COUNT(*) AS active_cryptocurrencies,
                MAX(last_updated) AS last_updated
            FROM latest_data
            """
            
            result = await self.db.execute(text(query))
            row = result.fetchone()
            
            if not row:
                # 返回默认值
                return MarketStats(
                    total_market_cap=0,
                    total_volume_24h=0,
                    market_cap_change_percentage_24h=0,
                    active_cryptocurrencies=0,
                    market_cap_percentage={
                        "bitcoin": 50.0,
                        "ethereum": 20.0,
                        "others": 30.0
                    },
                    last_updated=datetime.now()
                )
            
            # 获取 BTC 和 ETH 的市值占比
            btc_eth_query = """
            SELECT coin_id, market_cap
            FROM coin_data
            WHERE coin_id IN ('bitcoin', 'ethereum')
              AND time >= NOW() - INTERVAL '1 day'
              AND market_cap IS NOT NULL
            ORDER BY coin_id, time DESC
            """
            
            btc_eth_result = await self.db.execute(text(btc_eth_query))
            btc_market_cap = 0
            eth_market_cap = 0
            
            for btc_eth_row in btc_eth_result:
                if btc_eth_row.coin_id == 'bitcoin':
                    btc_market_cap = float(btc_eth_row.market_cap)
                elif btc_eth_row.coin_id == 'ethereum':
                    eth_market_cap = float(btc_eth_row.market_cap)
            
            total_market_cap = float(row.total_market_cap or 0)
            btc_percentage = (btc_market_cap / total_market_cap * 100) if total_market_cap > 0 else 0
            eth_percentage = (eth_market_cap / total_market_cap * 100) if total_market_cap > 0 else 0
            others_percentage = max(0, 100 - btc_percentage - eth_percentage)
            
            return MarketStats(
                total_market_cap=total_market_cap,
                total_volume_24h=float(row.total_volume_24h or 0),
                market_cap_change_percentage_24h=float(row.avg_market_cap_change or 0),
                active_cryptocurrencies=row.active_cryptocurrencies or 0,
                market_cap_percentage={
                    "bitcoin": round(btc_percentage, 1),
                    "ethereum": round(eth_percentage, 1),
                    "others": round(others_percentage, 1)
                },
                last_updated=row.last_updated or datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error getting market stats: {e}")
            # 返回默认值而不是抛出异常
            return MarketStats(
                total_market_cap=0,
                total_volume_24h=0,
                market_cap_change_percentage_24h=0,
                active_cryptocurrencies=0,
                market_cap_percentage={
                    "bitcoin": 50.0,
                    "ethereum": 20.0,
                    "others": 30.0
                },
                last_updated=datetime.now()
            )
    
    async def get_trending_coins(
        self,
        type: str = "gainers",
        limit: int = 10,
        timeframe: str = "24h"
    ) -> TrendingCoinsResponse:
        """获取热门币种（涨幅榜/跌幅榜）"""
        try:
            order_clause = "DESC" if type == "gainers" else "ASC"
            
            query = f"""
            SELECT DISTINCT ON (coin_id)
                coin_id, symbol, name, image,
                current_price, market_cap, market_cap_rank,
                total_volume, price_change_24h, price_change_percentage_24h,
                last_updated
            FROM coin_data
            WHERE time >= NOW() - INTERVAL '1 day'
              AND price_change_percentage_24h IS NOT NULL
              AND current_price IS NOT NULL
            ORDER BY coin_id, price_change_percentage_24h {order_clause}
            LIMIT {limit}
            """
            
            result = await self.db.execute(text(query))
            rows = result.fetchall()
            
            trending_coins = []
            for row in rows:
                coin_data = {
                    'coin_id': row.coin_id,
                    'symbol': row.symbol,
                    'name': row.name,
                    'image': self._get_local_image_url(row.coin_id, row.image),
                    'current_price': float(row.current_price) if row.current_price else None,
                    'market_cap': float(row.market_cap) if row.market_cap else None,
                    'market_cap_rank': row.market_cap_rank,
                    'total_volume': float(row.total_volume) if row.total_volume else None,
                    'price_change_24h': float(row.price_change_24h) if row.price_change_24h else None,
                    'price_change_percentage_24h': float(row.price_change_percentage_24h) if row.price_change_percentage_24h else None,
                    'last_updated': row.last_updated
                }
                trending_coins.append(CoinData(**coin_data))
            
            return TrendingCoinsResponse(
                type=type,
                timeframe=timeframe,
                data=trending_coins
            )
            
        except Exception as e:
            logger.error(f"Error getting trending coins: {e}")
            raise