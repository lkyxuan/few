# CoinGecko 数据采集器

这是一个用于从 CoinGecko API 采集加密货币数据并存储到 TimescaleDB 的 Python 脚本。

## 功能特点

- 每3分钟自动采集所有币种的市场数据
- 数据时间自动对齐到3分钟间隔（使用毫秒时间戳）
- 使用 TimescaleDB 存储时间序列数据（超表优化）
- 完整的错误处理和日志记录
- 支持环境变量配置
- 智能 TimescaleDB 版本兼容性处理
- 自动回退到标准 PostgreSQL 表（如果 TimescaleDB 不可用）

## 环境要求

- Python 3.8+
- PostgreSQL 14+ with TimescaleDB 2.17.2+
- CoinGecko Pro API 密钥
- Linux 系统（推荐 Ubuntu 22.04+）

## 安装步骤

1. 克隆仓库：
```bash
git clone <repository_url>
cd coingecko_fetch
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
```
然后编辑 `.env` 文件，填入你的配置信息：
```
DB_NAME=test
DB_USER=postgres
DB_PASSWORD=2450512223
DB_HOST=localhost
DB_PORT=5432
COINGECKO_API_KEY=your_api_key
```

4. 初始化数据库：
```bash
python init_timescaledb.py
```
这将自动创建 TimescaleDB 扩展、表和索引。

## 运行脚本

```bash
python main.py
```

脚本会自动：
- 立即执行一次数据采集
- 设置定时任务，每3分钟执行一次
- 将日志输出到控制台和 `coingecko_collector.log` 文件

## 项目结构

```
coingecko_fetch/
├── main.py                 # 主程序入口
├── config.py              # 配置管理
├── data_fetcher.py        # 数据获取模块
├── database.py            # 数据库操作模块
├── utils.py               # 工具函数
├── init_timescaledb.py    # 数据库初始化脚本
├── check_environment.py   # 环境检查脚本
├── requirements.txt       # Python 依赖
├── requirements.md        # 详细需求文档
├── TIMESCALEDB_TROUBLESHOOTING.md  # TimescaleDB 故障排除
└── 更新日志.md            # 更新日志
```

## 日志查看

你可以通过以下方式查看日志：
- 实时查看：`tail -f coingecko_collector.log`
- 查看错误：`grep ERROR coingecko_collector.log`

## 注意事项

1. 请确保你有足够的 CoinGecko Pro API 配额（每月至少需要 172,800 次调用）
2. 数据库需要足够的存储空间
3. 建议使用进程管理工具（如 supervisor）来保持脚本持续运行

## 数据库使用示例

查询最新数据：
```sql
-- 查询过去1小时的最新数据
SELECT 
    to_timestamp(time/1000) as time,
    coin_id,
    current_price,
    market_cap_rank
FROM coin_data
WHERE time >= (EXTRACT(EPOCH FROM NOW()) * 1000)::BIGINT - 3600000
ORDER BY market_cap_rank NULLS LAST
LIMIT 10;

-- 使用预定义视图查询最新价格
SELECT * FROM latest_prices LIMIT 10;

-- 查询24小时价格变化
SELECT * FROM price_changes_24h LIMIT 10;
```

## 故障排除

如果遇到 TimescaleDB 相关错误，请参考：
- `TIMESCALEDB_TROUBLESHOOTING.md` - 详细的故障排除指南
- 运行 `python check_environment.py` 检查环境配置

## 开发计划

- [ ] 分布式爬虫提升速度
- [ ] 数据压缩优化
- [ ] 实时数据流处理
- [ ] Web 管理界面