# DataBao 加密货币数据处理平台

> 高性能的加密货币数据同步、分析和展示系统

## 🚀 快速开始

DataBao是一个完整的加密货币数据处理平台，由4个核心模块组成：

- **DataSync** - 数据同步引擎（每3分钟同步）
- **DataInsight** - 指标计算引擎（实时计算16个技术指标）
- **DataView** - 前端展示系统（Next.js + FastAPI）
- **Monitor** - 统一监控系统（飞书/邮件告警）

### 系统架构

```
远程PostgreSQL ──▶ DataSync ──▶ DataInsight ──▶ DataView
 (数据源)        (数据同步)    (指标计算)      (前端展示)
                     │             │               │
                     ▼             ▼               ▼
              本地cryptodb     indicator_data   Web界面
            (分层存储架构)      (指标存储)      (用户交互)
                     │             │               │
                     └─────────────┼───────────────┘
                                   ▼
                            Monitor Service
                           (统一监控告警)
```

### 一键启动

```bash
# 检查所有服务状态
sudo systemctl status postgresql datasync datainsight databao-monitor

# 查看数据同步状态
cd datasync && python src/main.py status

# 查看指标计算状态  
cd datainsight && python src/main.py status

# 访问监控面板
curl http://localhost:9527/health
```

## 📦 核心模块

### 🔄 DataSync - 数据同步引擎
**状态**: ✅ 生产就绪

**核心功能**:
- 每3分钟从远程PostgreSQL同步加密货币数据
- 智能分层存储：热数据(SSD) + 温数据(HDD) + 冷数据(备份)
- 自动数据迁移和清理
- 断点续传和容错机制

**快速使用**:
```bash
cd datasync
python src/main.py sync      # 启动智能同步
python src/main.py status    # 查看同步状态
python src/main.py health    # 健康检查
```

### 📈 DataInsight - 指标计算引擎
**状态**: ✅ 生产就绪

**核心功能**:
- 实时计算16个技术指标（MA、RSI、MACD等）
- 3秒轮询 + 5秒安全缓冲的高效调度
- 批量计算：2秒完成45,000个指标结果
- 自动追赶滞后数据

**快速使用**:
```bash
cd datainsight
python src/main.py run       # 启动指标计算
python src/main.py status    # 查看计算状态
```

### 🖥️ DataView - 前端展示系统
**状态**: ✅ 已投入使用

**核心功能**:
- Next.js 15前端 + FastAPI后端
- 实时币种数据展示和搜索
- 高性能API和响应式设计
- 支持PC和移动端

**快速使用**:
```bash
cd dataview/frontend
npm run dev                  # 启动前端开发服务器

cd dataview/backend  
python run.py                # 启动后端API服务
```

### 📊 Monitor - 统一监控系统
**状态**: ✅ 生产就绪

**核心功能**:
- 集中式监控和告警管理
- 飞书机器人集成，支持@all报警
- Web管理界面和实时监控面板
- 多渠道通知路由

**快速使用**:
```bash
cd monitor
python src/main.py           # 启动监控服务
curl http://localhost:9527   # 访问监控面板
```

## 🗄️ 数据架构

### 分层存储策略
- **热数据**: 3.7TB NVMe SSD - 最近6个月数据
- **温数据**: 7.2TB SATA HDD - 6个月-4年历史数据  
- **冷数据**: 19TB SATA HDD - 4年以上归档数据

### 数据库设计
```sql
-- 主数据库: cryptodb
coin_data (分区表)
├── coin_data_hot      (SSD - 最近6个月)
├── coin_data_warm     (HDD - 6个月-4年)
└── coin_data_cold     (备份盘 - 4年以上)

indicator_data (分区表)
├── indicator_data_hot
├── indicator_data_warm
└── indicator_data_cold

-- 管理表
sync_logs, cleanup_logs, migration_logs
```

## ⚙️ 系统管理

### SystemD服务
```bash
# 服务管理
sudo systemctl start/stop/restart datasync
sudo systemctl start/stop/restart datainsight  
sudo systemctl start/stop/restart databao-monitor

# 查看服务状态
sudo systemctl status datasync datainsight databao-monitor

# 查看服务日志
sudo journalctl -u datasync -f
sudo journalctl -u datainsight -f
```

### 配置文件位置
- **DataSync**: `datasync/config/datasync.yml`
- **DataInsight**: `datainsight/config/datainsight.yml`
- **Monitor**: `monitor/config/monitor.yml`
- **DataView**: `dataview/backend/src/settings.py`

## 🔧 开发指南

### 项目结构
```
databao/
├── datasync/          # 数据同步模块
├── datainsight/       # 指标计算模块
├── dataview/          # 前端展示模块
├── monitor/           # 监控系统模块
├── docs/              # 文档中心
└── data/              # 数据存储目录
    ├── hot/           # 热数据存储
    ├── warm/          # 温数据存储
    └── cold/          # 冷数据存储
```

### 开发环境设置
```bash
# 1. 克隆项目
git clone <repository-url>
cd databao

# 2. 设置Python环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
cd datasync && pip install -r requirements.txt
cd ../datainsight && pip install -r requirements.txt
cd ../monitor && pip install -r requirements.txt
cd ../dataview/backend && pip install -r requirements.txt

# 4. 配置数据库
# 编辑各模块的配置文件，设置数据库连接信息

# 5. 启动服务
cd datasync && python src/main.py sync &
cd ../datainsight && python src/main.py run &
cd ../monitor && python src/main.py &
cd ../dataview/frontend && npm run dev &
```

## 📊 性能指标

- **数据同步延迟**: < 3分钟
- **指标计算延迟**: < 8秒
- **查询响应时间**: 热数据 < 100ms
- **计算性能**: 2秒完成45,000个指标
- **系统可用性**: > 99.9%

## 🛠️ 故障排查

### 常见问题
1. **服务无法启动**: 检查配置文件和环境变量
2. **数据同步失败**: 检查网络连接和数据库权限
3. **指标计算停止**: 检查数据库连接和内存使用
4. **监控告警异常**: 检查飞书机器人配置

### 日志查看
```bash
# 查看各服务日志
tail -f /var/log/databao/datasync.log
tail -f /var/log/databao/datainsight.log
tail -f /var/log/databao/monitor.log

# 查看系统服务日志
sudo journalctl -u datasync -f
sudo journalctl -u datainsight -f
sudo journalctl -u databao-monitor -f
```

## 📚 详细文档

- **[系统架构](docs/ARCHITECTURE.md)** - 详细的系统架构设计
- **[部署指南](docs/DEPLOYMENT.md)** - 完整的部署和配置指南
- **[模块文档](docs/)** - 各模块的详细文档

## 📄 许可证

MIT License - 查看 [LICENSE](LICENSE) 文件了解详情。

---

*最后更新: 2025-01-01*  
*版本: v3.0*  
*维护者: DataBao团队*