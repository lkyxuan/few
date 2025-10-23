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
    time BIGINT NOT NULL,                  -- Unix时间戳（毫秒），已对齐到3分钟，主键之一
    raw_time BIGINT,                       -- 原始采集的Unix时间戳（毫秒）
    coin_id VARCHAR(255) NOT NULL,         -- 代币ID，主键之一
    symbol VARCHAR(255),                   -- 代币符号
    name VARCHAR(255),                     -- 代币名称
    image TEXT,                            -- 代币图片URL
    current_price DECIMAL(40, 18),         -- 当前价格（提高精度）
    market_cap DECIMAL(40, 8),             -- 市值
    market_cap_rank INTEGER,               -- 市值排名
    fully_diluted_valuation DECIMAL(40, 8),-- 完全稀释估值
    total_volume DECIMAL(40, 8),           -- 24小时总交易量
    circulating_supply DECIMAL(40, 8),     -- 流通供应量
    max_supply DECIMAL(40, 8),             -- 最大供应量
    last_updated BIGINT,                   -- API数据最后更新时间戳（毫秒）
    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT, -- 数据行创建时间戳（毫秒）
    PRIMARY KEY (time, coin_id)
);

-- 创建索引
CREATE INDEX idx_coin_data_coin_id ON coin_data(coin_id);
CREATE INDEX idx_coin_data_time_desc ON coin_data(time DESC);
CREATE INDEX idx_coin_data_market_cap_rank ON coin_data(market_cap_rank);
CREATE INDEX idx_coin_data_raw_time ON coin_data(raw_time);

-- 转换为 TimescaleDB 超表
SELECT create_hypertable('coin_data', 'time', if_not_exists => TRUE);
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
- 采集时间（raw_time）：实际API调用时间的毫秒时间戳
- 存储时间（time）：自动对齐到3分钟的毫秒时间戳
  - 例如：
    - 10:00-10:02 的数据对齐到 10:00 (毫秒时间戳)
    - 10:03-10:05 的数据对齐到 10:03 (毫秒时间戳)
    - 10:06-10:08 的数据对齐到 10:06 (毫秒时间戳)
    - 10:09-10:11 的数据对齐到 10:09 (毫秒时间戳)
    - 以此类推...
  - 实现方式：
    ```python
    def align_time_to_3min(ms_timestamp):
        """将毫秒时间戳对齐到3分钟"""
        dt = datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc)
        minutes = dt.minute
        aligned_minutes = (minutes // 3) * 3
        aligned_dt = dt.replace(minute=aligned_minutes, second=0, microsecond=0)
        return int(aligned_dt.timestamp() * 1000)
    ```

## 4. 技术架构

### 4.1 数据库
- TimescaleDB

### 4.2 开发环境
- Python 3.8+
- PostgreSQL 14+ with TimescaleDB 2.17.2+
- 主要依赖：
  - requests==2.31.0
  - psycopg2-binary==2.9.9
  - python-dotenv==1.0.0
  - schedule==1.2.1

### 4.3 系统要求
- 操作系统：Linux (Ubuntu 22.04+ 推荐)
- 内存：至少 2GB RAM
- 存储：根据数据量需求，建议至少 100GB
- 网络：稳定的互联网连接用于 API 调用

## 5. 项目时间线

### 5.1 第一阶段（1周）
- 环境搭建
- 主数据表创建
- 基础数据采集功能 