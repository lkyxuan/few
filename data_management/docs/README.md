# DataBao 文档中心

> 简洁高效的文档导航，快速找到你需要的信息

## 🚀 快速导航

### 核心文档
- **[系统架构](ARCHITECTURE.md)** - 整体架构设计和组件关系
- **[部署指南](DEPLOYMENT.md)** - 从零开始的完整部署流程
- **[系统维护](system/MAINTENANCE.md)** - 日常维护和故障排查

### 模块文档
- **[DataSync](datasync/)** - 数据同步模块
- **[DataInsight](datainsight/)** - 指标计算模块  
- **[DataView](dataview/)** - 前端展示模块
- **[Monitor](monitor/)** - 监控系统模块

## 📦 模块概览

| 模块 | 状态 | 功能 | 文档 |
|------|------|------|------|
| **DataSync** | ✅ 生产就绪 | 数据同步、分层存储、自动迁移 | [模块文档](datasync/) |
| **DataInsight** | ✅ 生产就绪 | 指标计算、实时分析 | [模块文档](datainsight/) |
| **DataView** | ✅ 已投入使用 | 前端展示、用户交互 | [模块文档](dataview/) |
| **Monitor** | ✅ 生产就绪 | 统一监控、告警管理 | [模块文档](monitor/) |

## 🎯 按需查找

### 新手入门
1. [系统架构](ARCHITECTURE.md) - 了解整体设计
2. [部署指南](DEPLOYMENT.md) - 快速部署系统
3. [系统维护](system/MAINTENANCE.md) - 日常运维

### 开发者
1. [DataSync开发](datasync/) - 数据同步开发
2. [DataInsight开发](datainsight/) - 指标计算开发
3. [DataView开发](dataview/) - 前端开发
4. [Monitor开发](monitor/) - 监控系统开发

### 运维人员
1. [SystemD服务管理](system/SYSTEMD_SERVICES.md) - 服务管理
2. [系统维护](system/MAINTENANCE.md) - 故障排查
3. [监控配置](monitor/) - 监控设置

## 🔧 快速命令

### 服务管理
```bash
# 查看所有服务状态
sudo systemctl status postgresql datasync datainsight databao-monitor

# 启动/停止服务
sudo systemctl start/stop datasync
sudo systemctl start/stop datainsight
sudo systemctl start/stop databao-monitor

# 查看服务日志
sudo journalctl -u datasync -f
sudo journalctl -u datainsight -f
sudo journalctl -u databao-monitor -f
```

### 健康检查
```bash
# 检查数据同步状态
cd datasync && python src/main.py status

# 检查指标计算状态
cd datainsight && python src/main.py status

# 检查监控服务
curl http://localhost:9527/health
```

### 开发调试
```bash
# 启动开发模式
cd datasync && python src/main.py sync
cd datainsight && python src/main.py run
cd monitor && python src/main.py
cd dataview/frontend && npm run dev
```

## 📊 系统状态

### 当前版本
- **DataSync**: v2.0 - 生产就绪
- **DataInsight**: v2.0 - 生产就绪
- **DataView**: v1.0 - 已投入使用
- **Monitor**: v2.0 - 生产就绪

### 性能指标
- **数据同步延迟**: < 3分钟
- **指标计算延迟**: < 8秒
- **查询响应时间**: 热数据 < 100ms
- **系统可用性**: > 99.9%

## 🆘 获取帮助

### 常见问题
1. **服务启动失败** → 查看 [系统维护](system/MAINTENANCE.md)
2. **数据同步异常** → 查看 [DataSync文档](datasync/)
3. **指标计算停止** → 查看 [DataInsight文档](datainsight/)
4. **监控告警异常** → 查看 [Monitor文档](monitor/)

### 日志位置
- **DataSync**: `/var/log/databao/datasync.log`
- **DataInsight**: `/var/log/databao/datainsight.log`
- **Monitor**: `/var/log/databao/monitor.log`
- **系统日志**: `sudo journalctl -u <service-name>`

### 配置文件
- **DataSync**: `datasync/config/datasync.yml`
- **DataInsight**: `datainsight/config/datainsight.yml`
- **Monitor**: `monitor/config/monitor.yml`
- **DataView**: `dataview/backend/src/settings.py`

---

*最后更新: 2025-01-01*  
*维护者: DataBao团队*