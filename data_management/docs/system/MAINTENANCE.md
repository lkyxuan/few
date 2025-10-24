# DataBao 系统维护指南

> 日常维护和故障排查指南

## 🔧 日常维护

### 每日检查
```bash
# 检查所有服务状态
sudo systemctl status postgresql datasync datainsight databao-monitor

# 检查磁盘空间
df -h

# 检查内存使用
free -h

# 检查系统负载
uptime
```

### 每周检查
```bash
# 检查日志文件大小
du -sh /var/log/databao/*

# 检查数据库大小
psql -d cryptodb -c "SELECT pg_size_pretty(pg_database_size('cryptodb'));"

# 检查同步状态
cd datasync && python src/main.py status

# 检查指标计算状态
cd datainsight && python src/main.py status
```

### 每月检查
```bash
# 清理旧日志文件
sudo find /var/log/databao -name "*.log" -mtime +30 -delete

# 检查数据库性能
psql -d cryptodb -c "SELECT * FROM pg_stat_user_tables ORDER BY n_tup_ins DESC;"

# 更新系统包
sudo apt update && sudo apt upgrade -y
```

## 🚨 故障排查

### 服务无法启动

#### 1. 检查配置文件
```bash
# 验证配置文件语法
python src/main.py --config-check

# 检查环境变量
env | grep -E "(DB_|MONITOR_)"
```

#### 2. 检查端口占用
```bash
# 检查端口占用
netstat -tlnp | grep -E ':(5432|9527|3000|8000)'

# 杀死占用进程
sudo kill -9 <PID>
```

#### 3. 检查权限
```bash
# 检查文件权限
ls -la /databao/
ls -la /var/log/databao/

# 修复权限
sudo chown -R datasync:datasync /databao/
sudo chmod 755 /databao/
```

### 数据同步异常

#### 1. 检查网络连接
```bash
# 测试远程数据库连接
ping your_remote_host
telnet your_remote_host 5432

# 测试数据库连接
psql -h your_remote_host -U your_remote_user -d your_remote_db -c "SELECT 1;"
```

#### 2. 检查数据库权限
```bash
# 检查本地数据库权限
psql -d cryptodb -c "SELECT current_user, current_database();"

# 检查远程数据库权限
psql -h your_remote_host -U your_remote_user -d your_remote_db -c "SELECT current_user, current_database();"
```

#### 3. 检查数据完整性
```bash
# 检查数据同步状态
cd datasync && python src/main.py status

# 检查数据量
psql -d cryptodb -c "SELECT COUNT(*) FROM coin_data;"

# 检查最新数据时间
psql -d cryptodb -c "SELECT MAX(time) FROM coin_data;"
```

### 指标计算停止

#### 1. 检查数据源
```bash
# 检查coin_data表
psql -d cryptodb -c "SELECT COUNT(*) FROM coin_data WHERE time > NOW() - INTERVAL '1 hour';"

# 检查最新数据
psql -d cryptodb -c "SELECT MAX(time) FROM coin_data;"
```

#### 2. 检查计算状态
```bash
# 检查指标计算状态
cd datainsight && python src/main.py status

# 检查indicator_data表
psql -d cryptodb -c "SELECT COUNT(*) FROM indicator_data;"

# 检查最新指标
psql -d cryptodb -c "SELECT MAX(time) FROM indicator_data;"
```

#### 3. 重启计算服务
```bash
# 重启DataInsight服务
sudo systemctl restart datainsight

# 检查服务状态
sudo systemctl status datainsight

# 查看服务日志
sudo journalctl -u datainsight -f
```

### 监控告警异常

#### 1. 检查监控服务
```bash
# 检查监控服务状态
curl http://localhost:9527/health

# 检查监控配置
curl http://localhost:9527/config
```

#### 2. 检查Webhook配置
```bash
# 测试Webhook连接
curl -X POST http://localhost:9527/api/test/webhook

# 检查Webhook配置
cat monitor/config/webhooks.yml
```

#### 3. 检查通知渠道
```bash
# 检查飞书机器人
curl -X POST "your_webhook_url" -H "Content-Type: application/json" -d '{"msg_type":"text","content":{"text":"测试消息"}}'

# 检查邮件配置
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"
```

## 📊 性能监控

### 系统资源监控
```bash
# CPU使用率
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

# 内存使用率
free | grep Mem | awk '{printf "%.2f%%", $3/$2 * 100.0}'

# 磁盘使用率
df -h | grep -E "(/databao|/var/log)" | awk '{print $5}'

# 网络连接数
netstat -an | grep ESTABLISHED | wc -l
```

### 数据库性能监控
```bash
# 数据库大小
psql -d cryptodb -c "SELECT pg_size_pretty(pg_database_size('cryptodb'));"

# 表大小
psql -d cryptodb -c "SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"

# 连接数
psql -d cryptodb -c "SELECT count(*) FROM pg_stat_activity;"

# 慢查询
psql -d cryptodb -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### 应用性能监控
```bash
# 检查服务响应时间
time curl -s http://localhost:9527/health

# 检查数据库查询时间
psql -d cryptodb -c "EXPLAIN ANALYZE SELECT COUNT(*) FROM coin_data;"

# 检查日志文件大小
du -sh /var/log/databao/*
```

## 🔄 备份和恢复

### 数据库备份
```bash
# 全量备份
pg_dump -h localhost -U datasync -d cryptodb > backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
pg_dump -h localhost -U datasync -d cryptodb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# 增量备份（基于时间）
pg_dump -h localhost -U datasync -d cryptodb --data-only --where="time > '2025-01-01'" > incremental_backup.sql
```

### 配置备份
```bash
# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz datasync/config/ datainsight/config/ monitor/config/

# 备份日志文件
tar -czf logs_backup_$(date +%Y%m%d_%H%M%S).tar.gz /var/log/databao/
```

### 数据恢复
```bash
# 恢复数据库
psql -h localhost -U datasync -d cryptodb < backup_20250101_120000.sql

# 恢复压缩备份
gunzip -c backup_20250101_120000.sql.gz | psql -h localhost -U datasync -d cryptodb

# 恢复配置文件
tar -xzf config_backup_20250101_120000.tar.gz
```

## 🛠️ 维护脚本

### 健康检查脚本
```bash
#!/bin/bash
# health_check.sh

echo "=== DataBao 健康检查 ==="

# 检查服务状态
echo "1. 检查服务状态..."
sudo systemctl status postgresql datasync datainsight databao-monitor --no-pager

# 检查端口
echo "2. 检查端口..."
netstat -tlnp | grep -E ':(5432|9527|3000|8000)'

# 检查磁盘空间
echo "3. 检查磁盘空间..."
df -h | grep -E "(/databao|/var/log)"

# 检查内存
echo "4. 检查内存..."
free -h

# 检查数据库连接
echo "5. 检查数据库连接..."
psql -d cryptodb -c "SELECT 1;" > /dev/null 2>&1 && echo "数据库连接正常" || echo "数据库连接失败"

# 检查监控服务
echo "6. 检查监控服务..."
curl -s http://localhost:9527/health > /dev/null 2>&1 && echo "监控服务正常" || echo "监控服务异常"

echo "=== 健康检查完成 ==="
```

### 日志清理脚本
```bash
#!/bin/bash
# log_cleanup.sh

echo "=== 清理旧日志文件 ==="

# 清理30天前的日志
find /var/log/databao -name "*.log" -mtime +30 -delete

# 清理7天前的备份文件
find /databao/backups -name "*.sql" -mtime +7 -delete

# 清理临时文件
find /tmp -name "databao_*" -mtime +1 -delete

echo "=== 日志清理完成 ==="
```

## 📞 紧急联系

### 紧急故障处理
1. **服务完全停止**: 立即重启所有服务
2. **数据库损坏**: 从备份恢复数据
3. **磁盘空间不足**: 清理日志和临时文件
4. **网络中断**: 检查网络连接和防火墙

### 联系信息
- **技术支持**: 查看项目仓库Issue
- **紧急联系**: 通过飞书群组联系
- **文档更新**: 提交Pull Request

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*