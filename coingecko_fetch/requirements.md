# 加密货币数据分析系统需求文档

## 1. 项目概述

### 1.1 项目目标
开发一个加密货币数据采集系统，使用TimescaleDB存储时间序列数据，为后续分析提供基础。

### 1.2 项目范围
- 数据采集：从CoinGecko获取所有币种的原始市场数据
- 数据存储：使用TimescaleDB存储原始宽表数据
- 数据对齐：将采集时间自动对齐到3分钟（如10:00-10:02的数据对齐到10:00，10:03-10:05的数据对齐到10:03）

## 2. 数据库设计

### 2.1 主数据表（宽表，字段与API一致）
```sql
CREATE TABLE coin_data (
    time TIMESTAMPTZ,              -- 数据采集时间（已对齐到3分钟），主键之一
    raw_time TIMESTAMPTZ,          -- 原始采集时间（未对齐）
    coin_id VARCHAR(50),           -- 代币ID，如"quorium"
    symbol VARCHAR(20),            -- 代币符号，如"qgold"
    name VARCHAR(100),             -- 代币名称，如"Quorium"
    image TEXT,                    -- 币种图片URL
    current_price DECIMAL(40,8),   -- 当前价格
    market_cap DECIMAL(40,8),      -- 市值
    market_cap_rank INTEGER,       -- 市值排名
    fully_diluted_valuation DECIMAL(40,8), -- 完全稀释估值
    total_volume DECIMAL(40,8),    -- 24小时总交易量
    high_24h DECIMAL(40,8),        -- 24小时最高价
    low_24h DECIMAL(40,8),         -- 24小时最低价
    price_change_24h DECIMAL(40,8),-- 24小时价格变化
    price_change_percentage_24h DECIMAL(10,5), -- 24小时价格变化百分比
    market_cap_change_24h DECIMAL(40,8),      -- 24小时市值变化
    market_cap_change_percentage_24h DECIMAL(10,5), -- 24小时市值变化百分比
    circulating_supply DECIMAL(40,8),         -- 流通供应量
    total_supply DECIMAL(40,8),               -- 总供应量
    max_supply DECIMAL(40,8),                 -- 最大供应量
    ath DECIMAL(40,8),                        -- 历史最高价
    ath_change_percentage DECIMAL(10,5),      -- 距历史最高价变化百分比
    ath_date TIMESTAMPTZ,                     -- 历史最高价时间
    atl DECIMAL(40,8),                        -- 历史最低价
    atl_change_percentage DECIMAL(10,5),      -- 距历史最低价变化百分比
    atl_date TIMESTAMPTZ,                     -- 历史最低价时间
    last_updated TIMESTAMPTZ,                 -- API数据最后更新时间
    price_change_percentage_24h_in_currency DECIMAL(15,8),  -- 24小时价格变化百分比（币种计价）
    price_change_percentage_30d_in_currency DECIMAL(15,8),  -- 30天价格变化百分比
    price_change_percentage_7d_in_currency DECIMAL(15,8),   -- 7天价格变化百分比
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,       -- 数据入库时间
    PRIMARY KEY (time, coin_id)
);

-- 创建索引
CREATE INDEX idx_coin_data_coin_id ON coin_data(coin_id);
CREATE INDEX idx_coin_data_time ON coin_data(time);
CREATE INDEX idx_coin_data_market_cap_rank ON coin_data(market_cap_rank);
CREATE INDEX idx_coin_data_raw_time ON coin_data(raw_time);
```

## 3. 数据采集与处理

### 3.1 采集内容
按照api的所有字段

### 3.2 采集频率
- 每3分钟采集一次（可根据需求调整）
- 采集所有币种（约3000个）
- 每次API调用获取250个币种数据，需要12次API调用
- 每天API调用次数：480次采集 × 12次API调用 = 5,760次/天
- 每月API调用次数：5,760次/天 × 30天 = 172,800次/月
- API使用率：172,800 ÷ 500,000 ≈ 34.56%

### 3.3 数据来源
- CoinGecko Pro API `/coins/markets`

### 3.4 时间对齐处理
- 采集时间（raw_time）：实际API调用时间
- 存储时间（time）：自动对齐到3分钟
  - 例如：
    - 10:00-10:02 的数据对齐到 10:00
    - 10:03-10:05 的数据对齐到 10:03
    - 10:06-10:08 的数据对齐到 10:06
    - 10:09-10:11 的数据对齐到 10:09
    - 以此类推...
  - 实现方式：
    ```python
    def align_time_to_3min(timestamp):
        """将时间戳对齐到3分钟"""
        minutes = timestamp.minute
        aligned_minutes = (minutes // 3) * 3
        return timestamp.replace(minute=aligned_minutes, second=0, microsecond=0)
    ```

## 4. 技术架构

### 4.1 数据库
- TimescaleDB

### 4.2 开发环境
- Python 3.8+
- 主要依赖：
  - requests/pandas/sqlalchemy
  - python-dotenv

## 5. 项目时间线

### 5.1 第一阶段（1周）
- 环境搭建
- 主数据表创建
- 基础数据采集功能 