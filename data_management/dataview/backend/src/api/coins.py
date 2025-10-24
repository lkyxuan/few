from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from datetime import datetime

from database.connection import get_db
from services.coin_service import CoinService
from models.coin import (
    CoinListResponse, CoinData, CoinHistoryResponse, MarketStats, TrendingCoinsResponse,
    CoinQueryParams, HistoryQueryParams, TrendingQueryParams, ErrorResponse, Pagination
)

router = APIRouter(prefix="/coins", tags=["coins"])


@router.get(
    "",
    response_model=CoinListResponse,
    summary="获取币种列表（超快版）",
    description="基于最新时间点的超快币种查询，避免24小时数据扫描"
)
async def get_coins(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词（币种名称或符号）"),
    sort: str = Query("market_cap_rank", description="排序字段"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="排序方向"),
    db: AsyncSession = Depends(get_db)
):
    """
    超快获取币种列表

    基于用户的关键洞察：
    - 只查询最新时间点的数据，避免范围查询
    - 最新时间点数据量很小，查询极快
    - 不扫描24小时的历史数据
    """
    try:
        # 1. 获取最新时间点
        latest_time_query = text("SELECT MAX(time) as latest_time FROM coin_data")
        latest_time_result = await db.execute(latest_time_query)
        latest_time = latest_time_result.scalar()

        if not latest_time:
            return CoinListResponse(
                data=[],
                pagination=Pagination(page=page, limit=limit, total=0, total_pages=0),
                meta=None
            )

        # 2. 构建搜索条件
        search_condition = ""
        params = {
            "time_point": latest_time,
            "limit": limit,
            "offset": (page - 1) * limit
        }

        if search:
            search_condition = """
            AND (
                LOWER(coin_id) LIKE :search
                OR LOWER(symbol) LIKE :search
                OR LOWER(name) LIKE :search
            )
            """
            params["search"] = f"%{search.lower()}%"

        # 3. 获取总数
        count_query = text(f"""
        SELECT COUNT(*) as total
        FROM coin_data
        WHERE time = :time_point {search_condition}
        """)
        count_result = await db.execute(count_query, params)
        total = count_result.scalar() or 0

        # 4. 查询币种数据
        order_clause = f"ORDER BY {sort} {order.upper()} NULLS LAST"

        coins_query = text(f"""
        WITH coin_indicators AS (
            SELECT
                c.coin_id, c.symbol, c.name, c.image,
                c.current_price, c.market_cap, c.market_cap_rank,
                c.fully_diluted_valuation, c.total_volume,
                c.circulating_supply, c.max_supply,
                c.price_change_24h, c.price_change_percentage_24h,
                c.market_cap_change_24h, c.market_cap_change_percentage_24h,
                c.ath, c.ath_change_percentage, c.ath_date,
                c.atl, c.atl_change_percentage, c.atl_date,
                c.last_updated, c.time,
                MAX(CASE WHEN i.indicator_name = 'CAPITAL_INFLOW_INTENSITY_3M' THEN i.indicator_value END) as capital_inflow_intensity_3m,
                MAX(CASE WHEN i.indicator_name = 'VOLUME_CHANGE_RATIO_3M' THEN i.indicator_value END) as volume_change_ratio_3m,
                MAX(CASE WHEN i.indicator_name = 'AVG_VOLUME_3M_24H' THEN i.indicator_value END) as avg_volume_3m_24h
            FROM coin_data c
            LEFT JOIN indicator_data i ON c.coin_id = i.coin_id
                AND c.time = i.time
                AND i.indicator_name IN ('CAPITAL_INFLOW_INTENSITY_3M', 'VOLUME_CHANGE_RATIO_3M', 'AVG_VOLUME_3M_24H')
            WHERE c.time = :time_point {search_condition}
            GROUP BY c.coin_id, c.symbol, c.name, c.image,
                c.current_price, c.market_cap, c.market_cap_rank,
                c.fully_diluted_valuation, c.total_volume,
                c.circulating_supply, c.max_supply,
                c.price_change_24h, c.price_change_percentage_24h,
                c.market_cap_change_24h, c.market_cap_change_percentage_24h,
                c.ath, c.ath_change_percentage, c.ath_date,
                c.atl, c.atl_change_percentage, c.atl_date,
                c.last_updated, c.time
        )
        SELECT * FROM coin_indicators
        {order_clause}
        LIMIT :limit OFFSET :offset
        """)

        coins_result = await db.execute(coins_query, params)
        coins = [dict(row._mapping) for row in coins_result]

        # 5. 处理图片URL和数据类型
        processed_coins = []
        for coin in coins:
            # 转换数值类型
            for key, value in coin.items():
                if value is not None and key in [
                    'current_price', 'market_cap', 'fully_diluted_valuation',
                    'total_volume', 'circulating_supply', 'max_supply',
                    'price_change_24h', 'price_change_percentage_24h',
                    'market_cap_change_24h', 'market_cap_change_percentage_24h',
                    'ath', 'ath_change_percentage', 'atl', 'atl_change_percentage',
                    'capital_inflow_intensity_3m', 'volume_change_ratio_3m', 'avg_volume_3m_24h'
                ]:
                    coin[key] = float(value)

            # 转换图片URL为本地服务
            if coin.get('image'):
                coin['image'] = f"/api/v1/images/coin/{coin['coin_id']}"

            processed_coins.append(CoinData(**coin))

        total_pages = (total + limit - 1) // limit

        return CoinListResponse(
            data=processed_coins,
            pagination=Pagination(
                page=page,
                limit=limit,
                total=total,
                total_pages=total_pages
            ),
            meta=None
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "INTERNAL_ERROR", "message": str(e)}}
        )


@router.get(
    "/{coin_id}",
    response_model=CoinData,
    summary="获取币种详情",
    description="根据币种ID获取详细信息",
    responses={404: {"model": ErrorResponse, "description": "币种不存在"}}
)
async def get_coin(
    coin_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取单个币种的详细信息
    
    - **coin_id**: 币种ID，如 'bitcoin', 'ethereum'
    """
    try:
        coin_service = CoinService(db)
        coin = await coin_service.get_coin(coin_id)
        
        if not coin:
            raise HTTPException(
                status_code=404, 
                detail={
                    "error": {
                        "code": "COIN_NOT_FOUND",
                        "message": f"币种 '{coin_id}' 不存在",
                        "details": {"coin_id": coin_id}
                    }
                }
            )
        
        return coin
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取币种详情失败: {str(e)}")


@router.get(
    "/{coin_id}/history",
    response_model=CoinHistoryResponse,
    summary="获取币种历史数据",
    description="获取指定时间范围内的币种价格历史数据（OHLCV）"
)
async def get_coin_history(
    coin_id: str,
    start: datetime = Query(..., description="开始时间（ISO格式）"),
    end: datetime = Query(..., description="结束时间（ISO格式）"),
    interval: str = Query("1h", description="时间间隔（1m, 5m, 15m, 1h, 4h, 1d, 1w）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取币种历史价格数据
    
    - **coin_id**: 币种ID
    - **start**: 开始时间，ISO格式，如 '2024-01-01T00:00:00Z'
    - **end**: 结束时间，ISO格式
    - **interval**: 时间间隔
      - 1m: 1分钟
      - 5m: 5分钟  
      - 15m: 15分钟
      - 1h: 1小时
      - 4h: 4小时
      - 1d: 1天
      - 1w: 1周
    """
    try:
        # 验证时间范围
        if start >= end:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_TIME_RANGE",
                        "message": "开始时间必须早于结束时间",
                        "details": {"start": start, "end": end}
                    }
                }
            )
        
        # 验证间隔
        valid_intervals = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_INTERVAL",
                        "message": f"无效的时间间隔: {interval}",
                        "details": {"interval": interval, "valid_intervals": valid_intervals}
                    }
                }
            )
        
        coin_service = CoinService(db)
        return await coin_service.get_coin_history(coin_id, start, end, interval)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史数据失败: {str(e)}")


@router.get(
    "/{coin_id}/indicators",
    summary="获取币种指标时间线数据",
    description="获取指定币种的所有指标时间序列数据，用于多指标时间线图表"
)
async def get_coin_indicators(
    coin_id: str,
    start: datetime = Query(..., description="开始时间（ISO格式）"),
    end: datetime = Query(..., description="结束时间（ISO格式）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取币种指标时间线数据

    - **coin_id**: 币种ID（如 'bitcoin'）
    - **start**: 开始时间，ISO格式，如 '2025-09-10T00:00:00Z'
    - **end**: 结束时间，ISO格式

    返回所有可用指标的时间序列数据，格式为:
    ```
    {
      "coin_id": "bitcoin",
      "data": [
        {
          "time": "2025-09-19T10:00:00Z",
          "indicator_name": "PRICE_CHANGE_24H",
          "indicator_value": 2.5
        },
        ...
      ],
      "indicators": ["PRICE_CHANGE_24H", "VOLUME_CHANGE_1H", ...]
    }
    ```
    """
    try:
        # 验证时间范围
        if start >= end:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_TIME_RANGE",
                        "message": "开始时间必须早于结束时间",
                        "details": {"start": start, "end": end}
                    }
                }
            )

        # 查询指标数据
        indicators_query = text("""
        SELECT
            time,
            indicator_name,
            indicator_value
        FROM indicator_data
        WHERE coin_id = :coin_id
          AND time >= :start
          AND time <= :end
          AND indicator_value IS NOT NULL
        ORDER BY time ASC, indicator_name ASC
        """)

        params = {
            "coin_id": coin_id,
            "start": start,
            "end": end
        }

        result = await db.execute(indicators_query, params)
        rows = result.fetchall()

        if not rows:
            return {
                "coin_id": coin_id,
                "data": [],
                "indicators": [],
                "meta": {
                    "start": start,
                    "end": end,
                    "total_points": 0,
                    "total_indicators": 0
                }
            }

        # 转换数据格式
        data = []
        indicators_set = set()

        for row in rows:
            data.append({
                "time": row.time.isoformat() if row.time else None,
                "indicator_name": row.indicator_name,
                "indicator_value": float(row.indicator_value) if row.indicator_value is not None else None
            })
            indicators_set.add(row.indicator_name)

        indicators_list = sorted(list(indicators_set))

        return {
            "coin_id": coin_id,
            "data": data,
            "indicators": indicators_list,
            "meta": {
                "start": start,
                "end": end,
                "total_points": len(data),
                "total_indicators": len(indicators_list),
                "time_range": f"{start} - {end}"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标数据失败: {str(e)}")


