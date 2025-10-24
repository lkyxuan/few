# DataBao 快速开始指南

> 5分钟快速部署和运行 DataBao 系统

## 🚀 环境准备

### 系统要求
- Ubuntu 18.04+ 或 CentOS 7+
- Python 3.8+
- PostgreSQL 12+
- 至少 2GB 内存，10GB 磁盘空间

### 依赖安装
```bash
# 安装系统依赖
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib

# 或 CentOS/RHEL
sudo yum install python3 python3-pip postgresql postgresql-server postgresql-contrib
```

## 📦 快速部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd databao
```

### 2. 设置Python环境
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
cd datasync && pip install -r requirements.txt
cd ../datainsight && pip install -r requirements.txt
cd ../monitor && pip install -r requirements.txt
cd ../dataview/backend && pip install -r requirements.txt
```

### 3. 配置数据库
```bash
# 创建数据库
sudo -u postgres createdb cryptodb

# 创建用户
sudo -u postgres psql -c "CREATE USER datasync WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE cryptodb TO datasync;"

# 初始化数据库表
sudo -u postgres psql -d cryptodb -f datasync/sql/schema/01_create_tables.sql
sudo -u postgres psql -d cryptodb -f datasync/sql/indexes/02_create_indexes.sql
```

### 4. 配置环境变量
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

### 5. 配置服务
```bash
# 复制配置文件模板
cp datasync/config/datasync.yml.example datasync/config/datasync.yml
cp datainsight/config/datainsight.yml.example datainsight/config/datainsight.yml
cp monitor/config/monitor.yml.example monitor/config/monitor.yml

# 编辑配置文件，设置数据库连接信息
nano datasync/config/datasync.yml
nano datainsight/config/datainsight.yml
nano monitor/config/monitor.yml
```

## 🚀 启动服务

### 方式一：开发模式（推荐新手）
```bash
# 终端1：启动数据同步
cd datasync
python src/main.py sync

# 终端2：启动指标计算
cd datainsight
python src/main.py run

# 终端3：启动监控服务
cd monitor
python src/main.py

# 终端4：启动前端（可选）
cd dataview/frontend
npm install
npm run dev
```

### 方式二：生产模式（SystemD服务）
```bash
# 安装SystemD服务
sudo cp datasync/datasync.service /etc/systemd/system/
sudo cp datainsight/datainsight.service /etc/systemd/system/
sudo cp monitor/databao-monitor.service /etc/systemd/system/

# 重新加载SystemD配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl enable datasync datainsight databao-monitor
sudo systemctl start datasync datainsight databao-monitor

# 查看服务状态
sudo systemctl status datasync datainsight databao-monitor
```

## ✅ 验证部署

### 1. 检查服务状态
```bash
# 检查所有服务
sudo systemctl status postgresql datasync datainsight databao-monitor

# 检查数据同步状态
cd datasync && python src/main.py status

# 检查指标计算状态
cd datainsight && python src/main.py status

# 检查监控服务
curl http://localhost:9527/health
```

### 2. 查看日志
```bash
# 查看服务日志
sudo journalctl -u datasync -f
sudo journalctl -u datainsight -f
sudo journalctl -u databao-monitor -f

# 查看应用日志
tail -f /var/log/databao/datasync.log
tail -f /var/log/databao/datainsight.log
tail -f /var/log/databao/monitor.log
```

### 3. 访问Web界面
```bash
# 访问监控面板
curl http://localhost:9527

# 访问前端界面（如果已启动）
curl http://localhost:3000
```

## 🔧 基本操作

### 数据同步管理
```bash
cd datasync

# 查看同步状态
python src/main.py status

# 手动执行同步
python src/main.py test

# 健康检查
python src/main.py health

# 数据清理
python src/main.py cleanup

# 数据迁移
python src/main.py migrate
```

### 指标计算管理
```bash
cd datainsight

# 查看计算状态
python src/main.py status

# 启动计算服务
python src/main.py run

# 守护进程模式
python src/main.py daemon
```

### 监控服务管理
```bash
cd monitor

# 启动监控服务
python src/main.py

# 查看监控状态
curl http://localhost:9527/health

# 查看监控配置
curl http://localhost:9527/config
```

## 🛠️ 故障排查

### 常见问题

#### 1. 服务启动失败
```bash
# 检查配置文件
python src/main.py --config-check

# 检查数据库连接
python src/main.py health

# 查看详细错误
sudo journalctl -u <service-name> -f
```

#### 2. 数据同步异常
```bash
# 检查网络连接
ping your_remote_host

# 检查数据库权限
psql -h your_remote_host -U your_remote_user -d your_remote_db

# 查看同步日志
tail -f /var/log/databao/datasync.log
```

#### 3. 指标计算停止
```bash
# 检查数据库连接
cd datainsight && python src/main.py status

# 检查数据完整性
psql -d cryptodb -c "SELECT COUNT(*) FROM coin_data;"

# 重启计算服务
sudo systemctl restart datainsight
```

### 日志分析
```bash
# 查看错误日志
grep -i error /var/log/databao/*.log

# 查看警告日志
grep -i warn /var/log/databao/*.log

# 查看特定时间段的日志
journalctl --since "1 hour ago" -u datasync
```

## 📚 下一步

### 深入学习
1. [系统架构](ARCHITECTURE.md) - 了解整体设计
2. [模块文档](README.md) - 各模块详细文档
3. [系统维护](system/MAINTENANCE.md) - 运维指南

### 高级配置
1. [部署指南](DEPLOYMENT.md) - 生产环境部署
2. [SystemD服务管理](system/SYSTEMD_SERVICES.md) - 服务管理
3. [监控配置](monitor/) - 监控系统配置

### 开发指南
1. [DataSync开发](datasync/) - 数据同步开发
2. [DataInsight开发](datainsight/) - 指标计算开发
3. [DataView开发](dataview/) - 前端开发

## 🆘 获取帮助

如果遇到问题：
1. 查看相关模块的文档
2. 检查日志文件
3. 运行健康检查命令
4. 在项目仓库提交Issue

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*
