from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.coin_service import CoinService
from models.coin import MarketStats, TrendingCoinsResponse

router = APIRouter(prefix="/market", tags=["market"])


@router.get(
    "/stats",
    response_model=MarketStats,
    summary="获取市场统计",
    description="获取整体市场统计数据"
)
async def get_market_stats(db: AsyncSession = Depends(get_db)):
    """
    获取市场统计数据
    
    返回总市值、24小时交易量、活跃币种数量等统计信息
    """
    try:
        coin_service = CoinService(db)
        return await coin_service.get_market_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取市场统计失败: {str(e)}")


@router.get(
    "/trending",
    response_model=TrendingCoinsResponse,
    summary="获取热门币种",
    description="获取涨幅榜或跌幅榜"
)
async def get_trending_coins(
    type: str = Query("gainers", pattern="^(gainers|losers)$", description="类型：gainers（涨幅榜）或 losers（跌幅榜）"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    timeframe: str = Query("24h", description="时间范围"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取热门币种
    
    - **type**: 
      - gainers: 涨幅榜
      - losers: 跌幅榜
    - **limit**: 返回币种数量，最大50
    - **timeframe**: 时间范围（目前固定为24h）
    """
    try:
        coin_service = CoinService(db)
        return await coin_service.get_trending_coins(type, limit, timeframe)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门币种失败: {str(e)}")