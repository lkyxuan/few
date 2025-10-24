-- DataSync 数据库表结构创建脚本
-- 基于 docs/datasync/datasync.md 的设计

-- 创建币种基础数据主表（分区表）
CREATE TABLE coin_data (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_time TIMESTAMP WITH TIME ZONE NOT NULL,
    coin_id TEXT NOT NULL,
    symbol TEXT,
    name TEXT,
    image TEXT,
    current_price DECIMAL(20,8),
    market_cap DECIMAL(30,2),
    market_cap_rank INTEGER,
    fully_diluted_valuation DECIMAL(30,2),
    total_volume DECIMAL(30,2),
    circulating_supply DECIMAL(30,2),
    max_supply DECIMAL(30,2),
    last_updated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    price_change_percentage_24h DECIMAL(10,6),
    price_change_percentage_7d DECIMAL(10,6),
    price_change_percentage_30d DECIMAL(10,6),
    price_change_24h DECIMAL(20,8),
    market_cap_change_24h DECIMAL(30,2),
    market_cap_change_percentage_24h DECIMAL(10,6),
    ath DECIMAL(20,8),
    ath_change_percentage DECIMAL(10,6),
    ath_date TIMESTAMP WITH TIME ZONE,
    atl DECIMAL(20,8),
    atl_change_percentage DECIMAL(10,6),
    atl_date TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (time, coin_id)
) PARTITION BY RANGE (time);


-- 创建同步日志表
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    sync_type TEXT NOT NULL,
    last_sync_time TIMESTAMP WITH TIME ZONE NOT NULL,
    records_synced BIGINT DEFAULT 0,
    sync_status TEXT NOT NULL DEFAULT 'completed',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建远程清理日志表
CREATE TABLE cleanup_logs (
    id SERIAL PRIMARY KEY,
    cleanup_time TIMESTAMP WITH TIME ZONE NOT NULL,
    records_deleted BIGINT DEFAULT 0,
    cleanup_status TEXT NOT NULL DEFAULT 'completed',
    time_range_start TIMESTAMP WITH TIME ZONE,
    time_range_end TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建数据迁移日志表
CREATE TABLE migration_logs (
    id SERIAL PRIMARY KEY,
    migration_type TEXT NOT NULL,
    migration_time TIMESTAMP WITH TIME ZONE NOT NULL,
    records_migrated BIGINT DEFAULT 0,
    migration_status TEXT NOT NULL DEFAULT 'completed',
    source_partition TEXT NOT NULL,
    target_partition TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建分区表
-- 热数据分区（最近1年）
CREATE TABLE coin_data_hot PARTITION OF coin_data 
FOR VALUES FROM ('2024-01-01 00:00:00+00') TO ('2030-12-31 23:59:59+00');


-- 温数据分区（2-4年前）
CREATE TABLE coin_data_warm PARTITION OF coin_data 
FOR VALUES FROM ('2020-01-01 00:00:00+00') TO ('2024-01-01 00:00:00+00');


-- 冷数据分区（4年以上）
CREATE TABLE coin_data_cold PARTITION OF coin_data 
FOR VALUES FROM ('1900-01-01 00:00:00+00') TO ('2020-01-01 00:00:00+00');

