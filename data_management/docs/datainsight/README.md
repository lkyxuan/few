# DataInsight 指标计算模块

> 高性能的加密货币技术指标计算引擎

## 🎯 核心功能

- **实时计算**: 3秒轮询 + 5秒安全缓冲的高效调度
- **批量处理**: 一次查询9个时间点，内存计算16个指标
- **准实时响应**: 每3秒检查新数据，发现后等待5秒确保数据完整性
- **连续追赶**: 启动时自动连续计算所有滞后数据块
- **高效存储**: 批量写入indicator_data表，约2秒完成45,000个指标结果

## 🚀 快速开始

### 安装依赖
```bash
cd datainsight
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置数据库
```bash
# 编辑配置文件
nano config/datainsight.yml

# 设置环境变量
export LOCAL_DB_USER=datasync
export LOCAL_DB_PASSWORD=your_password
```

### 启动服务
```bash
# 开发模式
python src/main.py run

# 守护进程模式
python src/main.py daemon

# 生产模式（SystemD）
sudo systemctl start datainsight
sudo systemctl enable datainsight
```

## 📋 命令参考

### 基本命令
```bash
python src/main.py run       # 启动指标计算
python src/main.py daemon    # 守护进程模式
python src/main.py status    # 查看计算状态
python src/main.py test      # 测试计算功能
```

### 参数选项
```bash
python src/main.py <command> [options]

Options:
  --config, -c PATH    配置文件路径 (默认: config/datainsight.yml)
  --help, -h          显示帮助信息
```

## ⚙️ 配置说明

### 主要配置项
```yaml
# 数据库配置
database:
  local:
    host: localhost
    port: 5432
    name: cryptodb
    user: ${LOCAL_DB_USER}
    password: ${LOCAL_DB_PASSWORD}

# 计算配置
calculation:
  polling_interval: 3        # 轮询间隔（秒）
  safety_buffer: 5          # 安全缓冲时间（秒）
  batch_size: 9             # 批量查询时间点数
  max_workers: 4            # 最大并发worker数

# 指标配置
indicators:
  enabled:
    - sma_5
    - sma_10
    - sma_20
    - sma_50
    - ema_12
    - ema_26
    - rsi_14
    - macd
    - bollinger_bands
    - atr_14
    - volume_sma_20
    - price_change_24h
    - market_cap_change_24h
    - volume_change_24h
    - volatility_24h
    - trend_strength

# 监控配置
monitoring:
  enabled: true
  service_name: "datainsight"
  monitor_url: "http://localhost:9527"
```

## 📊 支持的指标

### 基础技术指标
- **SMA**: 简单移动平均线（5, 10, 20, 50周期）
- **EMA**: 指数移动平均线（12, 26周期）
- **RSI**: 相对强弱指数（14周期）
- **MACD**: 移动平均收敛散度
- **Bollinger Bands**: 布林带
- **ATR**: 平均真实波幅（14周期）

### 市场指标
- **Volume SMA**: 交易量移动平均（20周期）
- **Price Change**: 24小时价格变化
- **Market Cap Change**: 24小时市值变化
- **Volume Change**: 24小时交易量变化
- **Volatility**: 24小时波动率
- **Trend Strength**: 趋势强度

## 🔧 计算流程

### 1. 简化调度轮询
```python
# 每3秒检查数据库最新时间
while True:
    latest_time = get_latest_coin_data_time()
    if latest_time > last_calculated_time:
        trigger_calculation()
    await asyncio.sleep(3)
```

### 2. 安全缓冲等待
```python
# 发现新数据后等待5秒
if new_data_found:
    await asyncio.sleep(5)  # 确保DataSync完成数据写入
    start_calculation()
```

### 3. 高效批量计算
```python
# 一次查询9个关键时间点数据
time_points = get_9_time_points()
coin_data = query_coin_data(time_points)

# 内存计算16个指标
for coin_id in coin_data:
    indicators = calculate_16_indicators(coin_data[coin_id])
    save_indicators(indicators)
```

### 4. 连续追赶模式
```python
# 连续计算所有滞后数据块
while has_lagging_data():
    calculate_next_batch()
    update_progress()
```

## 📊 性能指标

- **轮询间隔**: 3秒
- **安全缓冲**: 5秒
- **计算延迟**: < 8秒（3秒检查 + 5秒缓冲）
- **批量大小**: 9个时间点
- **指标数量**: 16个指标
- **计算性能**: 2秒完成45,000个指标结果

## 🔧 故障排查

### 常见问题
1. **计算停止**: 检查数据库连接和内存使用
2. **数据不完整**: 检查DataSync同步状态
3. **指标异常**: 检查数据质量和计算逻辑
4. **性能问题**: 调整批量大小和并发数

### 日志查看
```bash
# 查看实时日志
tail -f /var/log/databao/datainsight.log

# 查看系统服务日志
sudo journalctl -u datainsight -f

# 查看错误日志
grep -i error /var/log/databao/datainsight.log
```

### 健康检查
```bash
# 检查计算状态
python src/main.py status

# 检查数据库连接
psql -d cryptodb -c "SELECT COUNT(*) FROM indicator_data;"

# 检查最新指标
psql -d cryptodb -c "SELECT MAX(time) FROM indicator_data;"
```

## 📚 详细文档

- **[技术设计](DESIGN.md)** - 详细的技术架构和实现
- **[服务部署](DEPLOYMENT.md)** - SystemD服务部署指南

## 🔗 相关链接

- [系统架构](../../ARCHITECTURE.md)
- [部署指南](../../DEPLOYMENT.md)
- [系统维护](../../system/MAINTENANCE.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*