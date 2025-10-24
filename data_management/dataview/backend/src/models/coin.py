from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


# 币种数据模型
class CoinData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    coin_id: str
    symbol: str
    name: str
    image: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    market_cap_rank: Optional[int] = None
    fully_diluted_valuation: Optional[Decimal] = None
    total_volume: Optional[Decimal] = None
    circulating_supply: Optional[Decimal] = None
    max_supply: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None
    price_change_percentage_24h: Optional[Decimal] = None
    market_cap_change_24h: Optional[Decimal] = None
    market_cap_change_percentage_24h: Optional[Decimal] = None
    ath: Optional[Decimal] = None
    ath_change_percentage: Optional[Decimal] = None
    ath_date: Optional[datetime] = None
    atl: Optional[Decimal] = None
    atl_change_percentage: Optional[Decimal] = None
    atl_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    time: Optional[datetime] = None  # 数据采集时间点（3分钟间隔）
    
    # 指标数据 - 交易量变化指标
    volume_change_1h: Optional[Decimal] = None
    volume_change_3h: Optional[Decimal] = None
    volume_change_24h: Optional[Decimal] = None
    volume_change_8h: Optional[Decimal] = None
    volume_change_3m: Optional[Decimal] = None
    volume_change_6m: Optional[Decimal] = None
    volume_change_9m: Optional[Decimal] = None
    
    # 价格变化指标
    price_change_3m: Optional[Decimal] = None
    price_change_6m: Optional[Decimal] = None
    price_change_12m: Optional[Decimal] = None
    
    # 平均指标
    avg_btc_eth: Optional[Decimal] = None
    avg_btc_eth_sol: Optional[Decimal] = None
    weighted_avg_btc_eth: Optional[Decimal] = None
    weighted_avg_btc_eth_sol: Optional[Decimal] = None
    weighted_avg_sol_eth_bnb: Optional[Decimal] = None

    # 核心自定义指标
    capital_inflow_intensity_3m: Optional[Decimal] = None
    volume_change_ratio_3m: Optional[Decimal] = None
    avg_volume_3m_24h: Optional[Decimal] = None


# 历史价格数据模型
class HistoricalData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    time: datetime
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[Decimal] = None


# 市场统计模型
class MarketStats(BaseModel):
    total_market_cap: Decimal
    total_volume_24h: Decimal
    market_cap_change_percentage_24h: Optional[Decimal] = None
    active_cryptocurrencies: int
    market_cap_percentage: dict = Field(default_factory=dict)
    last_updated: datetime


# 分页信息模型
class Pagination(BaseModel):
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=200)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


# 币种列表响应模型
class CoinListResponse(BaseModel):
    data: List[CoinData]
    pagination: Pagination
    meta: Optional[MarketStats] = None


# 币种历史数据响应模型
class CoinHistoryResponse(BaseModel):
    coin_id: str
    interval: str
    data: List[HistoricalData]


# 热门币种响应模型
class TrendingCoinsResponse(BaseModel):
    type: str  # 'gainers' or 'losers'
    timeframe: str
    data: List[CoinData]


# API 查询参数模型
class CoinQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    search: Optional[str] = None
    sort: str = Field(default="market_cap_rank")
    order: str = Field(default="asc", pattern="^(asc|desc)$")


class HistoryQueryParams(BaseModel):
    start: datetime
    end: datetime
    interval: str = Field(default="1h")


class TrendingQueryParams(BaseModel):
    type: str = Field(default="gainers", pattern="^(gainers|losers)$")
    limit: int = Field(default=10, ge=1, le=50)
    timeframe: str = Field(default="24h")


# 错误响应模型
class ErrorResponse(BaseModel):
    error: dict = Field(
        example={
            "code": "INVALID_PARAMETER",
            "message": "The parameter 'coin_id' is required",
            "details": {}
        }
    )