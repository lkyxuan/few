# DataSync 数据同步模块

> 高性能的加密货币数据同步引擎

## 🎯 核心功能

- **智能同步**: 每3分钟从远程PostgreSQL同步最新数据
- **分层存储**: 热数据(SSD) + 温数据(HDD) + 冷数据(备份)
- **自动迁移**: 定期将热数据迁移到温/冷存储
- **数据清理**: 自动清理远程数据库过期数据
- **断点续传**: 支持同步中断后从断点继续

## 🚀 快速开始

### 安装依赖
```bash
cd datasync
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置数据库
```bash
# 编辑配置文件
nano config/datasync.yml

# 设置环境变量
export LOCAL_DB_USER=datasync
export LOCAL_DB_PASSWORD=your_password
export REMOTE_DB_HOST=your_remote_host
export REMOTE_DB_USER=your_remote_user
export REMOTE_DB_PASSWORD=your_remote_password
```

### 启动服务
```bash
# 开发模式
python src/main.py sync

# 生产模式（SystemD）
sudo systemctl start datasync
sudo systemctl enable datasync
```

## 📋 命令参考

### 基本命令
```bash
python src/main.py sync      # 启动智能同步
python src/main.py test      # 单次同步测试
python src/main.py status    # 查看同步状态
python src/main.py health    # 健康检查
python src/main.py cleanup   # 数据清理
python src/main.py migrate   # 数据迁移
```

### 参数选项
```bash
python src/main.py <command> [options]

Options:
  --config, -c PATH    配置文件路径 (默认: config/datasync.yml)
  --dry-run           预览模式，不实际执行
  --help, -h          显示帮助信息
```

## ⚙️ 配置说明

### 主要配置项
```yaml
# 数据库配置
database:
  remote:
    host: ${REMOTE_DB_HOST}
    port: 5432
    name: ${REMOTE_DB_NAME}
    user: ${REMOTE_DB_USER}
    password: ${REMOTE_DB_PASSWORD}
    ssl_mode: require
  
  local:
    host: localhost
    port: 5432
    name: cryptodb
    user: ${LOCAL_DB_USER}
    password: ${LOCAL_DB_PASSWORD}

# 同步配置
sync:
  interval: 3m
  batch_size: 10000
  concurrent_workers: 10
  retry_max: 3

# 智能轮询配置
smart_polling:
  enabled: true
  polling_cycle_minutes: 3
  polling_window_start: 5
  polling_window_end: 30
  polling_interval_seconds: 2

# 存储配置
storage:
  hot_data_path: /databao_hot
  warm_data_path: /databao_warm
  cold_data_path: /databao_cold

# 迁移配置
migration:
  enabled: true
  schedule: "0 2 * * 0"  # 每周日凌晨2点
  hot_retention_days: 182
  warm_retention_days: 1460

# 清理配置
remote_cleanup:
  enabled: true
  retention_days: 60
  trigger_after_sync: true
  safety_check: true
```

## 📊 性能指标

- **同步频率**: 每3分钟
- **批量大小**: 10,000条/批次
- **并发数**: 10个worker
- **同步延迟**: < 3分钟
- **数据完整性**: 自动校验

## 🔧 故障排查

### 常见问题
1. **同步失败**: 检查网络连接和数据库权限
2. **数据不完整**: 运行健康检查命令
3. **迁移失败**: 检查存储空间和权限
4. **清理异常**: 检查本地数据完整性

### 日志查看
```bash
# 查看实时日志
tail -f /var/log/databao/datasync.log

# 查看系统服务日志
sudo journalctl -u datasync -f

# 查看错误日志
grep -i error /var/log/databao/datasync.log
```

### 健康检查
```bash
# 完整健康检查
python src/main.py health

# 检查数据库连接
psql -h localhost -U datasync -d cryptodb -c "SELECT 1;"

# 检查远程连接
psql -h your_remote_host -U your_remote_user -d your_remote_db -c "SELECT 1;"
```

## 📚 详细文档

- **[技术设计](DESIGN.md)** - 详细的技术架构和实现
- **[数据库配置](DATABASE.md)** - 数据库连接和配置说明
- **[使用示例](EXAMPLES.md)** - 监控接口使用示例

## 🔗 相关链接

- [系统架构](../../ARCHITECTURE.md)
- [部署指南](../../DEPLOYMENT.md)
- [系统维护](../../system/MAINTENANCE.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*
