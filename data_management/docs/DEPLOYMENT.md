# DataBao 部署指南

> 从零开始的完整部署流程

## 🚀 快速部署

### 1. 环境准备
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib git

# CentOS/RHEL
sudo yum install python3 python3-pip postgresql postgresql-server postgresql-contrib git
```

### 2. 克隆项目
```bash
git clone <repository-url>
cd databao
```

### 3. 数据库设置
```bash
# 启动PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres createdb cryptodb
sudo -u postgres psql -c "CREATE USER datasync WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cryptodb TO datasync;"

# 初始化数据库表
sudo -u postgres psql -d cryptodb -f datasync/sql/schema/01_create_tables.sql
sudo -u postgres psql -d cryptodb -f datasync/sql/indexes/02_create_indexes.sql
```

### 4. 配置环境
```bash
# 创建环境变量文件
cat > .env << EOF
# 数据库配置
LOCAL_DB_USER=datasync
LOCAL_DB_PASSWORD=your_password
REMOTE_DB_HOST=your_remote_host
REMOTE_DB_USER=your_remote_user
REMOTE_DB_PASSWORD=your_remote_password

# 监控配置
MONITOR_WEBHOOK_URL=your_webhook_url
EOF

# 加载环境变量
source .env
```

### 5. 安装依赖
```bash
# 安装各模块依赖
cd datasync && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../datainsight && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../monitor && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../dataview/backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
cd ../dataview/frontend && npm install
```

### 6. 配置服务
```bash
# 复制配置文件模板
cp datasync/config/datasync.yml.example datasync/config/datasync.yml
cp datainsight/config/datainsight.yml.example datainsight/config/datainsight.yml
cp monitor/config/monitor.yml.example monitor/config/monitor.yml

# 编辑配置文件
nano datasync/config/datasync.yml
nano datainsight/config/datainsight.yml
nano monitor/config/monitor.yml
```

## 🔧 生产部署

### SystemD服务配置
```bash
# 创建服务文件
sudo cp datasync/datasync.service /etc/systemd/system/
sudo cp datainsight/datainsight.service /etc/systemd/system/
sudo cp monitor/databao-monitor.service /etc/systemd/system/

# 重新加载SystemD
sudo systemctl daemon-reload

# 启动服务
sudo systemctl enable datasync datainsight databao-monitor
sudo systemctl start datasync datainsight databao-monitor
```

### 服务管理
```bash
# 查看服务状态
sudo systemctl status datasync datainsight databao-monitor

# 启动/停止服务
sudo systemctl start/stop datasync
sudo systemctl start/stop datainsight
sudo systemctl start/stop databao-monitor

# 重启服务
sudo systemctl restart datasync datainsight databao-monitor

# 查看服务日志
sudo journalctl -u datasync -f
sudo journalctl -u datainsight -f
sudo journalctl -u databao-monitor -f
```

## 🌐 前端部署

### 开发环境
```bash
cd dataview/frontend
npm run dev
```

### 生产环境
```bash
cd dataview/frontend
npm run build
npm start
```

### Nginx配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 监控配置

### 飞书机器人配置
1. 在飞书群中添加机器人
2. 获取Webhook URL
3. 配置到monitor.yml文件中

### 监控面板访问
```bash
# 访问监控面板
curl http://localhost:9527

# 查看健康状态
curl http://localhost:9527/health

# 查看配置信息
curl http://localhost:9527/config
```

## ✅ 部署验证

### 1. 服务状态检查
```bash
# 检查所有服务
sudo systemctl status postgresql datasync datainsight databao-monitor

# 检查端口占用
netstat -tlnp | grep -E ':(5432|9527|3000|8000)'
```

### 2. 功能测试
```bash
# 测试数据同步
cd datasync && python src/main.py status

# 测试指标计算
cd datainsight && python src/main.py status

# 测试监控服务
curl http://localhost:9527/health

# 测试前端服务
curl http://localhost:3000
```

### 3. 数据验证
```bash
# 检查数据库连接
psql -d cryptodb -c "SELECT COUNT(*) FROM coin_data;"

# 检查指标数据
psql -d cryptodb -c "SELECT COUNT(*) FROM indicator_data;"

# 检查同步日志
psql -d cryptodb -c "SELECT * FROM sync_logs ORDER BY created_at DESC LIMIT 5;"
```

## 🔧 故障排查

### 常见问题
1. **服务启动失败**: 检查配置文件和环境变量
2. **数据库连接失败**: 检查PostgreSQL服务和用户权限
3. **端口占用**: 检查端口占用情况
4. **权限问题**: 检查文件权限和用户权限

### 日志查看
```bash
# 查看系统日志
sudo journalctl -u <service-name> -f

# 查看应用日志
tail -f /var/log/databao/*.log

# 查看数据库日志
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 性能优化
```bash
# 检查系统资源
htop
df -h
free -h

# 检查数据库性能
psql -d cryptodb -c "SELECT * FROM pg_stat_activity;"

# 检查网络连接
netstat -an | grep ESTABLISHED
```

## 📚 相关文档

- [快速开始指南](QUICKSTART.md)
- [系统架构](ARCHITECTURE.md)
- [系统维护](system/MAINTENANCE.md)
- [模块文档](README.md)

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*