-- 创建币种基础信息表，优化搜索性能
-- 这个表存储币种的静态信息，不经常变化的数据

CREATE TABLE IF NOT EXISTS coin_info (
    coin_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    image TEXT,
    description TEXT,
    homepage TEXT,
    blockchain_site TEXT,

    -- 搜索优化字段
    search_name VARCHAR(255) GENERATED ALWAYS AS (LOWER(name)) STORED,
    search_symbol VARCHAR(50) GENERATED ALWAYS AS (LOWER(symbol)) STORED,
    search_id VARCHAR(255) GENERATED ALWAYS AS (LOWER(coin_id)) STORED,

    -- 元数据
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建搜索优化索引
CREATE INDEX IF NOT EXISTS idx_coin_info_search_name ON coin_info USING GIN (search_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_coin_info_search_symbol ON coin_info USING GIN (search_symbol gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_coin_info_search_id ON coin_info USING GIN (search_id gin_trgm_ops);

-- 创建复合文本搜索索引
CREATE INDEX IF NOT EXISTS idx_coin_info_fulltext ON coin_info USING GIN (
    (search_name || ' ' || search_symbol || ' ' || search_id) gin_trgm_ops
);

-- 创建普通索引用于精确匹配
CREATE INDEX IF NOT EXISTS idx_coin_info_symbol ON coin_info (symbol);
CREATE INDEX IF NOT EXISTS idx_coin_info_name ON coin_info (name);
CREATE INDEX IF NOT EXISTS idx_coin_info_active ON coin_info (is_active) WHERE is_active = true;

-- 创建更新时间戳的触发器
CREATE OR REPLACE FUNCTION update_coin_info_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_coin_info_timestamp
    BEFORE UPDATE ON coin_info
    FOR EACH ROW
    EXECUTE FUNCTION update_coin_info_timestamp();

-- 注释
COMMENT ON TABLE coin_info IS '币种基础信息表，存储不经常变化的币种静态数据，用于优化搜索性能';
COMMENT ON COLUMN coin_info.coin_id IS '币种唯一标识符，主键';
COMMENT ON COLUMN coin_info.name IS '币种全名';
COMMENT ON COLUMN coin_info.symbol IS '币种符号';
COMMENT ON COLUMN coin_info.image IS '币种图标URL';
COMMENT ON COLUMN coin_info.search_name IS '搜索优化：小写币种名称，自动生成';
COMMENT ON COLUMN coin_info.search_symbol IS '搜索优化：小写币种符号，自动生成';
COMMENT ON COLUMN coin_info.search_id IS '搜索优化：小写币种ID，自动生成';
COMMENT ON COLUMN coin_info.is_active IS '币种是否活跃，用于过滤不活跃币种';