#!/usr/bin/env python3
"""
币种数据模型
"""

from sqlalchemy import Column, String, DECIMAL, Integer, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP as PG_TIMESTAMP
from datetime import datetime
from .base import Base


class CoinData(Base):
    """币种数据模型"""
    
    __tablename__ = 'coin_data'
    
    # 主键字段
    time = Column(PG_TIMESTAMP(timezone=True), primary_key=True, nullable=False)
    coin_id = Column(String, primary_key=True, nullable=False)
    
    # 时间字段
    raw_time = Column(PG_TIMESTAMP(timezone=True), nullable=False)
    last_updated = Column(PG_TIMESTAMP(timezone=True))
    created_at = Column(PG_TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    # 基础信息
    symbol = Column(String)
    name = Column(String)
    image = Column(String)
    
    # 价格信息
    current_price = Column(DECIMAL(20, 8))
    price_change_24h = Column(DECIMAL(20, 8))
    price_change_percentage_24h = Column(DECIMAL)
    price_change_percentage_7d = Column(DECIMAL)
    price_change_percentage_30d = Column(DECIMAL)
    
    # 市值信息
    market_cap = Column(DECIMAL(30, 2))
    market_cap_rank = Column(Integer)
    market_cap_change_24h = Column(DECIMAL(30, 2))
    market_cap_change_percentage_24h = Column(DECIMAL)
    fully_diluted_valuation = Column(DECIMAL(30, 2))
    
    # 交易量和供应量
    total_volume = Column(DECIMAL(30, 2))
    circulating_supply = Column(DECIMAL(30, 2))
    max_supply = Column(DECIMAL(30, 2))
    
    # 历史高低点
    ath = Column(DECIMAL(20, 8))  # All Time High
    ath_change_percentage = Column(DECIMAL)
    ath_date = Column(PG_TIMESTAMP(timezone=True))
    
    atl = Column(DECIMAL(20, 8))  # All Time Low
    atl_change_percentage = Column(DECIMAL)
    atl_date = Column(PG_TIMESTAMP(timezone=True))
    
    def __repr__(self):
        return f"<CoinData(coin_id='{self.coin_id}', time='{self.time}', price={self.current_price})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'time': self.time,
            'coin_id': self.coin_id,
            'raw_time': self.raw_time,
            'symbol': self.symbol,
            'name': self.name,
            'image': self.image,
            'current_price': float(self.current_price) if self.current_price else None,
            'market_cap': float(self.market_cap) if self.market_cap else None,
            'market_cap_rank': self.market_cap_rank,
            'fully_diluted_valuation': float(self.fully_diluted_valuation) if self.fully_diluted_valuation else None,
            'total_volume': float(self.total_volume) if self.total_volume else None,
            'circulating_supply': float(self.circulating_supply) if self.circulating_supply else None,
            'max_supply': float(self.max_supply) if self.max_supply else None,
            'last_updated': self.last_updated,
            'created_at': self.created_at,
            'price_change_percentage_24h': float(self.price_change_percentage_24h) if self.price_change_percentage_24h else None,
            'price_change_percentage_7d': float(self.price_change_percentage_7d) if self.price_change_percentage_7d else None,
            'price_change_percentage_30d': float(self.price_change_percentage_30d) if self.price_change_percentage_30d else None,
            'price_change_24h': float(self.price_change_24h) if self.price_change_24h else None,
            'market_cap_change_24h': float(self.market_cap_change_24h) if self.market_cap_change_24h else None,
            'market_cap_change_percentage_24h': float(self.market_cap_change_percentage_24h) if self.market_cap_change_percentage_24h else None,
            'ath': float(self.ath) if self.ath else None,
            'ath_change_percentage': float(self.ath_change_percentage) if self.ath_change_percentage else None,
            'ath_date': self.ath_date,
            'atl': float(self.atl) if self.atl else None,
            'atl_change_percentage': float(self.atl_change_percentage) if self.atl_change_percentage else None,
            'atl_date': self.atl_date
        }