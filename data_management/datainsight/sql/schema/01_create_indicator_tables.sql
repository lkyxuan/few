-- DataInsight 指标数据表结构创建脚本
-- 基于 docs/datainsight/datainsight.md 的设计

-- 创建指标数据主表（纵表结构，时序分区）
CREATE TABLE indicator_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,      -- 指标计算时间
    coin_id TEXT NOT NULL,                       -- 币种ID
    indicator_name TEXT NOT NULL,                -- 指标名称（如：SMA_20, RSI_14, MACD等）
    timeframe TEXT NOT NULL,                     -- 时间颗粒度（如：1m, 5m, 1h, 4h, 1d等）
    indicator_value DECIMAL(20,8),               -- 指标数值
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),  -- 记录创建时间
    PRIMARY KEY (time, coin_id, indicator_name, timeframe)
) PARTITION BY RANGE (time);

-- 创建分区表
-- 热数据分区（最近1年）
CREATE TABLE indicator_data_hot PARTITION OF indicator_data 
FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2030-12-31 23:59:59+00');

-- 温数据分区（2-4年前）
CREATE TABLE indicator_data_warm PARTITION OF indicator_data 
FOR VALUES FROM ('2020-01-01 00:00:00+00') TO ('2024-01-01 00:00:00+00');

-- 冷数据分区（4年以上）
CREATE TABLE indicator_data_cold PARTITION OF indicator_data 
FOR VALUES FROM ('1900-01-01 00:00:00+00') TO ('2020-01-01 00:00:00+00');