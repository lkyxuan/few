# Monitor 监控系统模块

> 统一监控和告警管理系统

## 🎯 核心功能

- **集中监控**: 统一管理所有组件的运行状态和告警
- **智能路由**: 根据事件类型和级别路由到不同通知渠道
- **多渠道通知**: 支持飞书、Slack、邮件、短信等多种通知方式
- **Web管理**: 提供监控面板和配置管理界面
- **事件聚合**: 智能聚合相似事件，避免告警风暴

## 🚀 快速开始

### 安装依赖
```bash
cd monitor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置服务
```bash
# 编辑配置文件
nano config/monitor.yml
nano config/webhooks.yml

# 设置环境变量
export MONITOR_WEBHOOK_URL=your_webhook_url
export MONITOR_SERVICE_NAME=databao-monitor
```

### 启动服务
```bash
# 开发模式
python src/main.py

# 生产模式（SystemD）
sudo systemctl start databao-monitor
sudo systemctl enable databao-monitor
```

## 📋 命令参考

### 基本命令
```bash
python src/main.py           # 启动监控服务
python src/main.py --help    # 显示帮助信息
```

### 参数选项
```bash
python src/main.py [options]

Options:
  --config, -c PATH    配置文件路径 (默认: config/monitor.yml)
  --port PORT         服务端口 (默认: 9527)
  --host HOST         服务地址 (默认: 0.0.0.0)
  --help, -h          显示帮助信息
```

## ⚙️ 配置说明

### 主配置文件 (monitor.yml)
```yaml
# 服务配置
service:
  name: "databao-monitor"
  host: "0.0.0.0"
  port: 9527
  debug: false

# 数据库配置
database:
  host: localhost
  port: 5432
  name: cryptodb
  user: ${LOCAL_DB_USER}
  password: ${LOCAL_DB_PASSWORD}

# 通知配置
notifications:
  enabled: true
  default_channel: "general"
  channels:
    general:
      type: "webhook"
      url: "${MONITOR_WEBHOOK_URL}"
      timeout: 5
      retry_count: 2
    
    critical:
      type: "webhook"
      url: "${CRITICAL_WEBHOOK_URL}"
      timeout: 5
      retry_count: 3
      alert_users: ["@all"]

# 事件配置
events:
  sync_start:
    level: "info"
    silent: false
    channel: "general"
  
  sync_success:
    level: "info"
    silent: true
    channel: "general"
  
  sync_failure:
    level: "error"
    silent: false
    channel: "critical"
    alert_users: ["@all"]
    immediate: true

# 日志配置
logging:
  level: INFO
  format: json
  file: /var/log/databao/monitor.log
  rotate_days: 30
```

### Webhook路由配置 (webhooks.yml)
```yaml
# 飞书机器人配置
feishu:
  enabled: true
  webhook_url: "${FEISHU_WEBHOOK_URL}"
  timeout: 5
  retry_count: 2
  
  # 消息模板
  templates:
    sync_start: |
      🚀 DataSync 开始同步
      时间: {timestamp}
      表: {table}
      记录数: {records}
    
    sync_success: |
      ✅ DataSync 同步成功
      时间: {timestamp}
      表: {table}
      记录数: {records}
      耗时: {duration}s
    
    sync_failure: |
      ❌ DataSync 同步失败
      时间: {timestamp}
      错误: {error}
      耗时: {duration}s

# Slack配置
slack:
  enabled: false
  webhook_url: "${SLACK_WEBHOOK_URL}"
  timeout: 5
  retry_count: 2

# 邮件配置
email:
  enabled: false
  smtp_host: "smtp.gmail.com"
  smtp_port: 587
  username: "${EMAIL_USERNAME}"
  password: "${EMAIL_PASSWORD}"
  from_email: "monitor@databao.com"
  to_emails: ["admin@databao.com"]
```

## 🌐 Web API

### 健康检查
```bash
# 检查服务状态
curl http://localhost:9527/health

# 检查配置
curl http://localhost:9527/config

# 查看统计信息
curl http://localhost:9527/stats
```

### 事件发送
```bash
# 发送自定义事件
curl -X POST http://localhost:9527/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "custom_event",
    "level": "info",
    "message": "自定义事件",
    "details": {"key": "value"}
  }'
```

### 监控面板
```bash
# 访问监控面板
curl http://localhost:9527/dashboard

# 查看事件历史
curl http://localhost:9527/api/events/history

# 查看告警统计
curl http://localhost:9527/api/alerts/stats
```

## 📊 监控指标

### 系统指标
- **服务状态**: 运行时间、内存使用、CPU使用
- **事件统计**: 总事件数、成功数、失败数
- **通知统计**: 发送成功数、失败数、重试数
- **响应时间**: API响应时间、数据库查询时间

### 业务指标
- **同步事件**: 同步开始、成功、失败事件
- **计算事件**: 指标计算开始、完成、错误事件
- **清理事件**: 数据清理开始、完成、错误事件
- **迁移事件**: 数据迁移开始、完成、错误事件

## 🔧 故障排查

### 常见问题
1. **服务启动失败**: 检查端口占用和配置文件
2. **通知发送失败**: 检查Webhook URL和网络连接
3. **事件丢失**: 检查数据库连接和事件队列
4. **性能问题**: 调整并发数和超时配置

### 日志查看
```bash
# 查看实时日志
tail -f /var/log/databao/monitor.log

# 查看系统服务日志
sudo journalctl -u databao-monitor -f

# 查看错误日志
grep -i error /var/log/databao/monitor.log
```

### 健康检查
```bash
# 检查服务状态
curl http://localhost:9527/health

# 检查数据库连接
psql -d cryptodb -c "SELECT 1;"

# 检查Webhook连接
curl -X POST http://localhost:9527/api/test/webhook
```

## 📚 详细文档

- **[部署架构](ARCHITECTURE.md)** - 监控系统部署架构
- **[系统设计](DESIGN.md)** - 详细的监控系统设计

## 🔗 相关链接

- [系统架构](../../ARCHITECTURE.md)
- [部署指南](../../DEPLOYMENT.md)
- [系统维护](../../system/MAINTENANCE.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*