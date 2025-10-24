# DataBao 监控服务

DataBao 集中式监控服务，为 DataSync、DataInsight、DataView 提供统一的监控和告警功能。

## ✨ 功能特性

- 🎯 **集中式管理**: 所有监控规则在一处配置
- 📱 **飞书机器人**: 支持发送到不同飞书群，成功消息静音、失败消息报警
- 🤖 **AI诊断友好**: 监控消息包含完整诊断信息，可直接复制给AI分析
- ⚙️ **灵活配置**: 不同事件类型、级别可路由到不同通知渠道
- 📊 **Web管理界面**: 实时监控面板和配置管理
- 🔄 **实时重载**: 修改配置文件后可热重载，无需重启服务

## 🚀 快速启动

### 1. 安装依赖和初始化
```bash
cd /databao/monitor
./start.sh install
```

### 2. 配置Webhook（重要！）
编辑配置文件：
```bash
nano config/webhooks.yml
```

配置文件已经为你预设了常用的监控规则：
- 监控1：DataSync同步成功 → 发到飞书群（静音）
- 监控2：DataSync同步失败 → 发到飞书群（报警@all）  
- 监控3：清理任务成功 → 发到飞书群（静音）
- 监控4：清理任务失败 → 发到飞书群（报警@all）
- 监控5：数据迁移成功 → 发到运维群
- ...等等

所有webhook现在都指向你提供的地址：
`https://open.larksuite.com/open-apis/bot/v2/hook/dc63e98e-24fd-490f-89e4-039a169d7451`

如果你想要不同类型的消息发到不同群，只需要：
1. 在对应飞书群中添加自定义机器人
2. 复制webhook地址
3. 在配置文件中替换相应的URL

### 3. 启动服务

#### 前台启动（用于测试）
```bash
./start.sh start
```

#### 后台启动（生产环境）
```bash
./start.sh start -d
```

#### 其他命令
```bash
./start.sh status    # 查看服务状态
./start.sh stop      # 停止服务
./start.sh restart   # 重启服务
```

### 4. 访问管理界面
服务启动后，访问: http://localhost:9527/dashboard

在管理界面中你可以：
- 📊 查看实时监控统计
- 📋 浏览最近的监控事件
- ⚙️ 查看当前配置规则
- 🧪 发送测试事件
- 🔄 重新加载配置

## 📡 API接口

### 发送监控事件
```bash
curl -X POST http://localhost:9527/api/events \\
  -H "Content-Type: application/json" \\
  -d '{
    "service": "datasync",
    "event_type": "sync_success", 
    "level": "info",
    "message": "测试同步成功",
    "details": {"table": "coin_data"},
    "metrics": {"records": 1000}
  }'
```

### 查看最近事件
```bash
curl http://localhost:9527/api/events?limit=10
```

### 查看统计信息
```bash
curl http://localhost:9527/api/stats
```

### 重新加载配置
```bash
curl -X POST http://localhost:9527/api/config/reload
```

## 🧪 测试监控系统

### 1. 发送测试事件
```bash
# 成功事件测试（会发送静音消息）
curl -X POST http://localhost:9527/api/test-event \\
  -H "Content-Type: application/json" \\
  -d '{"service": "datasync", "message": "测试同步成功事件"}'

# 失败事件测试（会发送报警消息并@all）
curl -X POST http://localhost:9527/api/events \\
  -H "Content-Type: application/json" \\
  -d '{
    "service": "datasync",
    "event_type": "sync_failure",
    "level": "error", 
    "message": "测试同步失败事件",
    "details": {"error": "连接超时"},
    "metrics": {"duration": 30}
  }'
```

### 2. 测试DataSync集成
确保DataSync正在使用新的监控客户端：
```bash
cd /databao/datasync
# 运行同步任务，会自动发送监控事件到中央监控服务
python src/main.py sync --dry-run
```

## 📁 目录结构

```
/databao/monitor/
├── src/
│   ├── main.py                 # 服务入口
│   ├── core/
│   │   ├── config_manager.py   # 配置管理
│   │   └── event_router.py     # 事件路由
│   ├── api/
│   │   └── monitor_api.py      # REST API
│   └── integrations/
│       ├── webhook_router.py   # Webhook路由
│       └── diagnostic_formatter.py  # 诊断消息格式化
├── config/
│   ├── monitor.yml            # 服务配置
│   └── webhooks.yml           # Webhook路由规则
├── requirements.txt           # Python依赖
├── start.sh                  # 启动脚本
└── databao-monitor.service   # systemd服务文件
```

## ⚙️ 配置说明

### webhook配置示例
```yaml
routing_rules:
  # 成功事件 -> 静音群
  - name: "datasync_success"
    conditions:
      service: "datasync"
      event_types: ["sync_success"]
      levels: ["info"]
    webhook:
      type: "feishu"
      url: "https://open.larksuite.com/open-apis/bot/v2/hook/your-success-webhook"
      silent: true          # 静音模式
      at_users: []          # 不@任何人
    enabled: true

  # 失败事件 -> 报警群  
  - name: "datasync_failure"
    conditions:
      service: "datasync"
      event_types: ["sync_failure"] 
      levels: ["error", "critical"]
    webhook:
      type: "feishu"
      url: "https://open.larksuite.com/open-apis/bot/v2/hook/your-alert-webhook"
      silent: false         # 非静音
      at_users: ["@all"]    # @所有人
    enabled: true
```

## 🔧 生产部署

### 使用systemd管理服务
```bash
# 安装systemd服务
sudo cp /databao/monitor/databao-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable databao-monitor
sudo systemctl start databao-monitor

# 查看状态
sudo systemctl status databao-monitor

# 查看日志
sudo journalctl -u databao-monitor -f
```

## 🐛 故障排除

### 查看日志
```bash
# 查看服务日志
tail -f /var/log/databao/monitor.log

# 查看systemd日志
sudo journalctl -u databao-monitor -f
```

### 常见问题

1. **端口占用**: 修改 `config/monitor.yml` 中的端口配置
2. **Webhook发送失败**: 检查网络连接和webhook URL是否正确
3. **配置重载失败**: 检查YAML语法是否正确
4. **权限问题**: 确保 `/var/log/databao` 目录权限正确

### 测试连通性
```bash
# 测试服务健康状态
curl http://localhost:9527/health

# 测试webhook连通性（通过发送测试事件）
./start.sh status
```

## 🎯 下一步

监控系统现在已经准备就绪！你可以：

1. **启动监控服务**: `./start.sh start -d`
2. **测试消息发送**: 访问 http://localhost:9527/dashboard 发送测试事件
3. **运行DataSync**: 数据同步时会自动发送监控消息到飞书群
4. **自定义配置**: 根据需要修改 `config/webhooks.yml` 配置不同群组

有任何问题请查看日志或联系开发团队！