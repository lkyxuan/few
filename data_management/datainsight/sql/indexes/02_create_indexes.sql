-- DataInsight 指标数据表索引优化脚本

-- 时间范围查询优化
CREATE INDEX idx_indicator_data_time_desc ON indicator_data (time DESC);

-- 币种查询优化
CREATE INDEX idx_indicator_data_coin_id ON indicator_data (coin_id);

-- 指标名称查询优化
CREATE INDEX idx_indicator_data_indicator_name ON indicator_data (indicator_name);

-- 时间颗粒度查询优化
CREATE INDEX idx_indicator_data_timeframe ON indicator_data (timeframe);

-- 复合索引：按币种、指标名称和时间颗粒度查询
CREATE INDEX idx_indicator_data_coin_indicator_timeframe ON indicator_data (coin_id, indicator_name, timeframe);

-- 复合索引：按时间和币种查询（用于时序分析）
CREATE INDEX idx_indicator_data_time_coin ON indicator_data (time, coin_id);

-- 复合索引：按指标名称、时间颗粒度和时间查询（用于特定指标的时序查询）
CREATE INDEX idx_indicator_data_indicator_timeframe_time ON indicator_data (indicator_name, timeframe, time DESC);

-- 复合索引：按币种和时间颗粒度查询（用于获取特定币种的所有时间框架数据）
CREATE INDEX idx_indicator_data_coin_timeframe_time ON indicator_data (coin_id, timeframe, time DESC);