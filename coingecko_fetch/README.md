# CoinGecko 数据采集器

这是一个用于从 CoinGecko API 采集加密货币数据并存储到 TimescaleDB 的 Python 脚本。

## 功能特点

- 每3分钟自动采集所有币种的市场数据
- 数据时间自动对齐到3分钟间隔
- 使用 TimescaleDB 存储时间序列数据
- 完整的错误处理和日志记录
- 支持环境变量配置

## 环境要求

- Python 3.8+
- TimescaleDB
- CoinGecko Pro API 密钥

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
DB_NAME=timedb
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
COINGECKO_API_KEY=your_api_key
```

4. 确保 TimescaleDB 已经创建了必要的表（参考 requirements.md 中的表结构）

## 运行脚本

```bash
python coingecko_collector.py
```

脚本会自动：
- 立即执行一次数据采集
- 设置定时任务，每3分钟执行一次
- 将日志输出到控制台和 `coingecko_collector.log` 文件

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
SELECT 
    time,
    coin_id,
    current_price,
    market_cap_rank
FROM coin_data
WHERE time >= NOW() - INTERVAL '1 hour'
ORDER BY market_cap_rank NULLS LAST
LIMIT 10;
```

ToDo：

​     分布式爬虫提升速度