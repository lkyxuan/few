-- DataSync 索引创建脚本
-- 优化查询性能的关键索引

-- coin_data 表的索引
CREATE INDEX idx_coin_data_coin_id ON coin_data (coin_id);
CREATE INDEX idx_coin_data_time_desc ON coin_data (time DESC);
CREATE INDEX idx_coin_data_market_cap_rank ON coin_data (market_cap_rank);
CREATE INDEX idx_coin_data_price_change_24h ON coin_data (price_change_percentage_24h);
CREATE INDEX idx_coin_data_raw_time ON coin_data (raw_time);
CREATE INDEX idx_coin_data_ath ON coin_data (ath);
CREATE INDEX idx_coin_data_ath_date ON coin_data (ath_date);
CREATE INDEX idx_coin_data_atl ON coin_data (atl);

-- indicator_data 表的索引
CREATE INDEX idx_indicator_data_coin_id ON indicator_data (coin_id);
CREATE INDEX idx_indicator_data_indicator_name ON indicator_data (indicator_name);
CREATE INDEX idx_indicator_data_time_desc ON indicator_data (time DESC);
CREATE INDEX idx_indicator_data_timeframe ON indicator_data (timeframe);

-- 日志表索引
CREATE INDEX idx_sync_logs_sync_type ON sync_logs (sync_type);
CREATE INDEX idx_sync_logs_last_sync_time ON sync_logs (last_sync_time);
CREATE INDEX idx_sync_logs_sync_status ON sync_logs (sync_status);

CREATE INDEX idx_cleanup_logs_cleanup_time ON cleanup_logs (cleanup_time);
CREATE INDEX idx_cleanup_logs_cleanup_status ON cleanup_logs (cleanup_status);

CREATE INDEX idx_migration_logs_migration_time ON migration_logs (migration_time);
CREATE INDEX idx_migration_logs_migration_type ON migration_logs (migration_type);