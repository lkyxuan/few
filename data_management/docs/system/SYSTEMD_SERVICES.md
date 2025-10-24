# SystemD 服务管理

> DataBao 系统服务统一管理指南

## 🚀 服务概览

DataBao系统包含以下SystemD服务：

| 服务名称 | 描述 | 端口 | 依赖 |
|----------|------|------|------|
| `postgresql` | 数据库服务 | 5432 | - |
| `datasync` | 数据同步服务 | - | postgresql |
| `datainsight` | 指标计算服务 | - | postgresql |
| `databao-monitor` | 监控服务 | 9527 | postgresql |

## 📋 服务管理命令

### 基本操作
```bash
# 启动服务
sudo systemctl start <service-name>

# 停止服务
sudo systemctl stop <service-name>

# 重启服务
sudo systemctl restart <service-name>

# 重新加载配置
sudo systemctl reload <service-name>

# 查看服务状态
sudo systemctl status <service-name>

# 启用开机自启
sudo systemctl enable <service-name>

# 禁用开机自启
sudo systemctl disable <service-name>
```

### 批量操作
```bash
# 启动所有DataBao服务
sudo systemctl start postgresql datasync datainsight databao-monitor

# 停止所有DataBao服务
sudo systemctl stop datasync datainsight databao-monitor

# 重启所有DataBao服务
sudo systemctl restart datasync datainsight databao-monitor

# 查看所有服务状态
sudo systemctl status postgresql datasync datainsight databao-monitor
```

## 🔧 服务配置

### DataSync服务配置
```ini
# /etc/systemd/system/datasync.service
[Unit]
Description=DataBao DataSync Service
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=datasync
Group=datasync
WorkingDirectory=/databao/datasync
ExecStart=/databao/datasync/venv/bin/python src/main.py sync
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=datasync

# 环境变量
Environment=LOCAL_DB_USER=datasync
Environment=LOCAL_DB_PASSWORD=your_password
Environment=REMOTE_DB_HOST=your_remote_host
Environment=REMOTE_DB_USER=your_remote_user
Environment=REMOTE_DB_PASSWORD=your_remote_password

# 自动重启机制（每30分钟）
RuntimeMaxSec=1800

[Install]
WantedBy=multi-user.target
```

### DataInsight服务配置
```ini
# /etc/systemd/system/datainsight.service
[Unit]
Description=DataBao DataInsight Service
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=datasync
Group=datasync
WorkingDirectory=/databao/datainsight
ExecStart=/databao/datainsight/venv/bin/python src/main.py run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=datainsight

# 环境变量
Environment=LOCAL_DB_USER=datasync
Environment=LOCAL_DB_PASSWORD=your_password

# 自动重启机制（每30分钟）
RuntimeMaxSec=1800

[Install]
WantedBy=multi-user.target
```

### Monitor服务配置
```ini
# /etc/systemd/system/databao-monitor.service
[Unit]
Description=DataBao Monitor Service
After=postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=datasync
Group=datasync
WorkingDirectory=/databao/monitor
ExecStart=/databao/monitor/venv/bin/python src/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=databao-monitor

# 环境变量
Environment=LOCAL_DB_USER=datasync
Environment=LOCAL_DB_PASSWORD=your_password
Environment=MONITOR_WEBHOOK_URL=your_webhook_url

[Install]
WantedBy=multi-user.target
```

## 📊 服务监控

### 查看服务状态
```bash
# 查看所有服务状态
sudo systemctl status postgresql datasync datainsight databao-monitor

# 查看特定服务状态
sudo systemctl status datasync

# 查看服务是否启用
sudo systemctl is-enabled datasync

# 查看服务是否运行
sudo systemctl is-active datasync
```

### 查看服务日志
```bash
# 查看实时日志
sudo journalctl -u datasync -f

# 查看最近日志
sudo journalctl -u datasync -n 100

# 查看特定时间段的日志
sudo journalctl -u datasync --since "1 hour ago"

# 查看错误日志
sudo journalctl -u datasync -p err

# 查看所有服务日志
sudo journalctl -u postgresql -u datasync -u datainsight -u databao-monitor
```

### 服务性能监控
```bash
# 查看服务资源使用
sudo systemctl show datasync --property=MemoryCurrent,CPUUsageNSec

# 查看服务启动时间
sudo systemctl show datasync --property=ActiveEnterTimestamp

# 查看服务重启次数
sudo systemctl show datasync --property=NRestarts
```

## 🔧 故障排查

### 服务启动失败
```bash
# 查看详细错误信息
sudo journalctl -u datasync -n 50

# 检查配置文件
sudo systemctl cat datasync

# 检查服务依赖
sudo systemctl list-dependencies datasync

# 手动启动服务
sudo -u datasync /databao/datasync/venv/bin/python src/main.py sync
```

### 服务频繁重启
```bash
# 查看重启原因
sudo journalctl -u datasync --since "1 hour ago" | grep -i restart

# 检查资源使用
sudo systemctl show datasync --property=MemoryCurrent,CPUUsageNSec

# 检查配置文件
sudo systemctl cat datasync | grep -E "(Restart|RestartSec)"
```

### 服务无法停止
```bash
# 强制停止服务
sudo systemctl kill datasync

# 查看进程
ps aux | grep datasync

# 强制杀死进程
sudo kill -9 <PID>
```

## 🛠️ 维护操作

### 更新服务配置
```bash
# 编辑服务文件
sudo systemctl edit datasync

# 重新加载配置
sudo systemctl daemon-reload

# 重启服务
sudo systemctl restart datasync
```

### 禁用/启用服务
```bash
# 禁用服务
sudo systemctl disable datasync

# 启用服务
sudo systemctl enable datasync

# 查看服务状态
sudo systemctl is-enabled datasync
```

### 查看服务依赖
```bash
# 查看服务依赖
sudo systemctl list-dependencies datasync

# 查看反向依赖
sudo systemctl list-dependencies datasync --reverse

# 查看服务关系
sudo systemctl show datasync --property=Wants,Requires
```

## 📈 性能优化

### 服务资源限制
```ini
# 在服务文件中添加资源限制
[Service]
# 内存限制
MemoryLimit=1G
# CPU限制
CPUQuota=50%
# 文件描述符限制
LimitNOFILE=65536
```

### 日志管理
```bash
# 配置日志轮转
sudo nano /etc/systemd/journald.conf

# 设置日志大小限制
[Journal]
SystemMaxUse=100M
SystemMaxFileSize=10M
```

### 自动重启配置
```ini
# 在服务文件中配置自动重启
[Service]
# 总是重启
Restart=always
# 重启间隔
RestartSec=10
# 最大重启次数
StartLimitBurst=5
# 重启时间窗口
StartLimitIntervalSec=60
```

## 🔍 调试技巧

### 查看服务详细信息
```bash
# 查看服务完整信息
sudo systemctl show datasync

# 查看服务属性
sudo systemctl show datasync --property=ActiveState,SubState,LoadState

# 查看服务环境变量
sudo systemctl show datasync --property=Environment
```

### 测试服务配置
```bash
# 测试服务配置
sudo systemctl daemon-reload
sudo systemctl start datasync
sudo systemctl status datasync

# 查看服务日志
sudo journalctl -u datasync -f
```

### 服务调试模式
```bash
# 以调试模式启动服务
sudo systemctl edit datasync
# 添加：
# [Service]
# Environment=DEBUG=true
# StandardOutput=journal
# StandardError=journal

# 重新加载并重启
sudo systemctl daemon-reload
sudo systemctl restart datasync
```

## 📚 相关文档

- [系统维护](MAINTENANCE.md)
- [部署指南](../DEPLOYMENT.md)
- [快速开始](../QUICKSTART.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*