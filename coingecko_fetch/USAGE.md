# 使用说明

## 快速开始

### 1. 环境检查
在运行程序前，建议先检查环境配置：
```bash
python check_environment.py
```

### 2. 数据库初始化
如果是首次运行，需要初始化数据库：
```bash
python init_timescaledb.py
```

### 3. 运行程序

#### 方式一：直接运行
```bash
python main.py
```

#### 方式二：使用守护进程（推荐生产环境）
```bash
# 启动守护进程
nohup bash daemon.sh &

# 查看守护进程状态
ps aux | grep daemon.sh

# 停止守护进程
pkill -f daemon.sh
```

## 文件说明

### 核心文件
- `main.py` - 主程序入口
- `config.py` - 配置管理
- `data_fetcher.py` - 数据获取模块
- `database.py` - 数据库操作模块
- `utils.py` - 工具函数

### 脚本文件
- `init_timescaledb.py` - 数据库初始化脚本
- `check_environment.py` - 环境检查脚本
- `daemon.sh` - 守护进程脚本

### 配置文件
- `requirements.txt` - Python 依赖
- `.env` - 环境变量（可选，使用 config.py 中的默认配置）

## 监控和日志

### 日志文件
- `coingecko_collector.log` - 主程序日志
- `daemon.log` - 守护进程日志

### 查看日志
```bash
# 实时查看主程序日志
tail -f coingecko_collector.log

# 查看错误日志
grep ERROR coingecko_collector.log

# 查看守护进程日志
tail -f daemon.log
```

### 状态监控
程序会定期发送状态报告到配置的 Webhook URL，包括：
- 采集时间
- 采集币种数
- 成功/失败页数
- 总耗时
- 成功率
- 最小市值
- 健康状态

## 故障排除

### 常见问题

1. **TimescaleDB 扩展错误**
   - 参考 `TIMESCALEDB_TROUBLESHOOTING.md`
   - 运行 `python init_timescaledb.py` 重新初始化

2. **数据库连接失败**
   - 检查 PostgreSQL 服务是否运行
   - 验证 `config.py` 中的数据库配置

3. **API 请求失败**
   - 检查网络连接
   - 验证 CoinGecko API 密钥
   - 检查 API 配额使用情况

4. **程序无法启动**
   - 运行 `python check_environment.py` 检查环境
   - 检查 Python 依赖是否安装完整

### 调试模式
在 `main.py` 中取消注释以下行来启用调试模式：
```python
# 立即执行一次采集任务（调试用）
collect_all_data()
```

## 性能优化

### 数据库优化
- TimescaleDB 超表自动优化时间序列查询
- 定期清理旧数据（可选）
- 监控数据库连接池使用情况

### 采集优化
- 调整 `COINS_PER_PAGE` 参数（默认 250）
- 调整 `MAX_RETRIES` 重试次数（默认 3）
- 调整采集频率（默认每3分钟）

## 维护建议

### 日常维护
- 定期检查日志文件大小
- 监控磁盘空间使用
- 检查程序运行状态

### 定期任务
- 每周检查 API 使用量
- 每月评估存储需求
- 定期备份数据库

## 安全注意事项

1. **API 密钥安全**
   - 不要在代码中硬编码 API 密钥
   - 使用环境变量或配置文件管理敏感信息

2. **数据库安全**
   - 使用强密码
   - 限制数据库访问权限
   - 定期更新数据库版本

3. **系统安全**
   - 定期更新系统补丁
   - 使用防火墙限制访问
   - 监控异常活动

## 联系支持

如遇到问题，请：
1. 查看相关日志文件
2. 运行环境检查脚本
3. 参考故障排除文档
4. 检查项目更新日志
