# DataBao AI 助手指南

> 为后续AI提供项目的重要配置和运维信息

## 🚨 重要的环境信息

### Python环境配置
**DataBao项目的所有模块都使用虚拟环境！**

```bash
# 各模块的虚拟环境位置
/databao/datasync/venv/         # DataSync虚拟环境
/databao/datainsight/venv/      # DataInsight虚拟环境  
/databao/monitor/venv/          # Monitor虚拟环境

# SystemD服务配置必须使用虚拟环境的Python
ExecStart=/databao/datasync/venv/bin/python /databao/datasync/src/main.py
# 不是: /usr/bin/python3 (这会导致 ModuleNotFoundError)
```

### 数据库环境变量
```bash
# 本地数据库连接
LOCAL_DB_USER=datasync
LOCAL_DB_PASSWORD=datasync2025

# 远程数据库连接
REMOTE_DB_HOST=95.216.186.216
REMOTE_DB_PORT=5432
REMOTE_DB_NAME=timedb
REMOTE_DB_USER=coingecko
REMOTE_DB_PASSWORD=Coingecko@2025#DB
```

### 🌐 局域网访问配置（重要配置）
**DataView服务配置为支持局域网访问，使用固定IP地址 192.168.5.124**

```bash
# 服务器IP配置
DATABAO_SERVER_IP=192.168.5.124

# 前端配置 (next.config.ts)
allowedDevOrigins: ['192.168.5.124']  # 允许跨域访问

# 后端API代理配置
destination: 'http://192.168.5.124:8080/api/:path*'

# 访问地址
http://192.168.5.124:3000        # DataView前端
http://192.168.5.124:8080/docs   # FastAPI文档
```

**⚠️ 重要说明**：
- 系统专门配置为使用局域网地址，不是纯本地localhost配置
- Next.js已配置跨域支持，支持从192.168.5.124访问
- 后端API代理专门指向192.168.5.124:8080
- 所有启动命令使用 `--host 0.0.0.0` 绑定所有网络接口

### 目录权限设置
```bash
# 日志目录必须存在且有正确权限
sudo mkdir -p /var/log/databao
sudo chown -R qiji:qiji /var/log/databao
sudo chmod -R 755 /var/log/databao

# 数据目录权限
sudo chown -R qiji:qiji /databao
```

## 🔧 SystemD服务管理

### 服务配置文件位置
- DataSync: `/etc/systemd/system/datasync.service` (✅ 已配置代理+自动重启)
- DataInsight: `/etc/systemd/system/datainsight.service` (✅ 已配置自动重启) 
- Monitor: `/etc/systemd/system/databao-monitor.service`

### 重启服务的标准流程
```bash
# 1. 停止服务
sudo systemctl stop datasync

# 2. 重新加载配置（如果修改了服务文件）
sudo systemctl daemon-reload

# 3. 启动服务
sudo systemctl start datasync

# 4. 检查状态
sudo systemctl status datasync

# 5. 查看日志
sudo journalctl -u datasync -f
```

### 常见启动问题及解决方案

#### 1. ModuleNotFoundError: No module named 'sqlalchemy'
**原因**: SystemD服务使用了系统Python而不是虚拟环境
**解决**: 修改服务文件中的ExecStart路径使用虚拟环境Python
```bash
# 正确的配置
ExecStart=/databao/datasync/venv/bin/python /databao/datasync/src/main.py
# 错误的配置
ExecStart=/usr/bin/python3 /databao/datasync/src/main.py
```

#### 2. PermissionError: [Errno 13] Permission denied: '/var/log/databao/datasync.log'
**原因**: 日志目录不存在或权限不正确
**解决**: 创建目录并设置正确权限
```bash
sudo mkdir -p /var/log/databao
sudo chown -R qiji:qiji /var/log/databao
```

#### 3. PostgreSQL客户端证书权限问题
**原因**: 服务以非root用户运行时访问PostgreSQL证书权限不足
**解决**: 修改服务以root用户运行（推荐）
```bash
# 在服务文件中设置
User=root
Group=qiji
```

#### 4. 进程冲突 ⚠️ 常见问题！
**原因**: 已有DataBao进程在运行（通常是手动启动的）
**现象**: 服务启动成功但有重复进程，消耗过多CPU资源
**解决**: 先停止所有现有进程再启动SystemD服务
```bash
# 查找所有DataBao进程
ps aux | grep -E "(datasync|datainsight|monitor)" | grep -v grep

# 停止所有SystemD服务
sudo systemctl stop datasync datainsight databao-monitor

# 停止手动进程（如果存在）
sudo kill <PID1> <PID2> <PID3>

# 重新启动服务
sudo systemctl start datasync
sudo systemctl start datainsight
sudo systemctl start databao-monitor
```

#### 5. 数据库连接失败
**原因**: 环境变量未正确设置
**解决**: 检查服务文件中的Environment变量设置

#### 6. 远程数据库连接问题 🆕
**原因**: SystemD服务缺少网络代理配置
**现象**: 第一轮查询成功但后续查询卡住，长时间同步滞后
**解决**: 在服务配置中添加代理环境变量
```bash
Environment=https_proxy=http://127.0.0.1:7890
Environment=http_proxy=http://127.0.0.1:7890
Environment=all_proxy=socks5://127.0.0.1:7891
```

#### 7. 长时间运行连接问题 🆕
**原因**: 长期运行导致连接池、内存或网络连接积累问题
**解决**: 配置自动重启机制
```bash
# 在服务配置中添加
RuntimeMaxSec=1800  # 30分钟后自动重启
```

## 📊 监控消息修改记录

### 同步进度消息改进 (2025-08-31)
**修改目的**: 将监控消息从显示记录数改为显示实际同步时间

**修改文件**:
1. `/databao/datasync/src/core/sync_manager.py:384` - 传入真实的同步时间
2. `/databao/datasync/src/monitoring/monitor_client.py:257-259` - 调整消息格式

**效果对比**:
```
# 修改前
消息: 同步表 coin_data 进度: 10,000 条记录（最新数据: 批次完成: 10,000条）

# 修改后  
消息: 同步表 coin_data 进度: 10,000 条记录（最新数据: 2025-08-31 22:18:00+08:00）
```

**时间字段说明**:
- 使用的是`coin_data.time`字段（同步时间点，3分钟间隔）
- 不是`coin_data.raw_time`字段（原始数据时间）

## 🗄️ 数据库架构要点

### coin_data表结构
```sql
-- 关键时间字段
time TIMESTAMP WITH TIME ZONE NOT NULL,      -- 同步时间点（分区键）
raw_time TIMESTAMP WITH TIME ZONE NOT NULL,  -- 原始数据时间
```

### 分区策略
- `coin_data_hot` - 热数据（最近6个月，SSD）
- `coin_data_warm` - 温数据（6个月-4年，HDD）  
- `coin_data_cold` - 冷数据（4年以上，备份盘）

## 📁 文档结构
```
docs/
├── README.md           # 文档中心导航
├── ARCHITECTURE.md     # 整体架构
├── DEPLOYMENT.md       # 部署指南
├── datasync/           # DataSync模块文档
├── datainsight/        # DataInsight模块文档
├── dataview/           # DataView模块文档（预留）
├── monitor/            # Monitor模块文档
└── system/            # 系统级文档
```

## 🚀 项目启动流程

### 完整启动顺序
**重要**: 必须按以下顺序启动，确保依赖关系正确！

```bash
# 1. 确保PostgreSQL数据库运行
sudo systemctl status postgresql
sudo systemctl start postgresql  # 如果未运行

# 2. 检查并清理可能的进程冲突
ps aux | grep -E "(datasync|datainsight|monitor)" | grep -v grep
# 如发现手动进程，使用: sudo kill <PID>

# 3. 按顺序启动SystemD服务
sudo systemctl start datasync      # 先启动数据同步
sudo systemctl start datainsight   # 再启动指标分析
sudo systemctl start databao-monitor  # 最后启动监控

# 4. 验证所有服务状态
sudo systemctl status datasync datainsight databao-monitor
```

### 停止所有服务
```bash
# 停止所有DataBao服务
sudo systemctl stop datasync datainsight databao-monitor

# 检查是否有残留进程
ps aux | grep -E "(datasync|datainsight|monitor)" | grep -v grep

# 清理残留进程（如果有）
sudo kill <PID>
```

### 重启所有服务
```bash
# 完整重启流程
sudo systemctl stop datasync datainsight databao-monitor
sudo systemctl daemon-reload  # 如果修改过服务配置
sudo systemctl start datasync
sudo systemctl start datainsight  
sudo systemctl start databao-monitor
```

## ⚡ 快速命令参考

### 检查服务状态
```bash
sudo systemctl status postgresql datasync datainsight databao-monitor
```

### 查看同步状态
```bash
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 python3 /databao/datasync/src/main.py status
```

### 监控面板
```bash
curl http://localhost:9527/health
```

### 测试程序
```bash
cd /databao/datasync
source venv/bin/activate
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 python src/main.py health
```

### 启动DataView服务
```bash
# 启动后端API (端口8080) - 已优化指标数据查询和图片服务
cd /databao/dataview/backend
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 \
PYTHONPATH=/databao/dataview/backend/src \
./venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8080

# 启动前端Web (端口3000) - 智能图片组件，API响应时间1.2秒
cd /databao/dataview/frontend
npm run dev -- --hostname 0.0.0.0

# 访问地址 (🔥 重要：使用局域网地址访问)
# 本地访问:  http://localhost:3000
# 局域网访问: http://192.168.5.124:3000 (推荐用于测试和演示)
# API文档:    http://192.168.5.124:8080/docs (超快币种查询API)
# 图片服务:  http://192.168.5.124:8080/api/v1/images/coin/{coin_id} (智能加载)

# ⚠️ 注意：前端配置了专门的局域网访问支持
# Next.js配置: allowedDevOrigins: ['192.168.5.124']
# 后端代理:    destination: 'http://192.168.5.124:8080/api/:path*'
```

### 查看实时日志
```bash
# 查看DataSync日志
sudo journalctl -u datasync -f

# 查看DataInsight日志
sudo journalctl -u datainsight -f

# 查看Monitor日志
sudo journalctl -u databao-monitor -f

# 查看所有服务日志
sudo journalctl -u datasync -u datainsight -u databao-monitor -f
```

## 🔄 开发状态
- ✅ **DataSync**: 生产就绪，已在运行同步CoinGecko数据
- ✅ **DataInsight**: 生产就绪，已实现数据库通知机制
- ✅ **Monitor**: 生产就绪，已修复虚拟环境配置问题
- ✅ **DataView**: 已投入使用，前后端服务正常运行 (1.2s响应时间)，完整指标数据显示，智能图片服务

## 🧪 正确的测试方法和错误防范

### ⚠️ 测试陷阱：不要创造虚假问题

**错误的测试方式**：
```bash
# ❌ 错误：手动运行时不提供必要参数
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 /databao/datasync/venv/bin/python /databao/datasync/src/main.py health

# 这会导致使用默认相对路径 config/datasync.yml
# 从/databao目录运行时会找不到配置文件
# 但这并不代表SystemD服务有问题！
```

**正确的测试方式**：
```bash
# ✅ 正确：模拟SystemD服务的实际运行方式
cd /databao/datasync
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 ./venv/bin/python src/main.py health --config /databao/datasync/config/datasync.yml

# 或者从正确的工作目录运行
cd /databao/datasync
LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 ./venv/bin/python src/main.py health
```

### 🔍 问题诊断流程

在声称发现"bug"之前，必须按以下顺序检查：

1. **检查SystemD服务配置**：
   ```bash
   cat /etc/systemd/system/datasync.service
   # 确认ExecStart行的完整命令和参数
   ```

2. **检查服务实际运行状态**：
   ```bash
   sudo systemctl status datasync
   sudo journalctl -u datasync -n 20
   ```

3. **确认问题的真实性**：
   - 问题是否在生产环境中真实存在？
   - 还是只是测试方法不当造成的？

4. **使用与生产环境一致的测试命令**：
   ```bash
   # 完全模拟SystemD服务的启动方式
   cd /databao/datasync
   LOCAL_DB_USER=datasync LOCAL_DB_PASSWORD=datasync2025 \
   REMOTE_DB_HOST=95.216.186.216 \
   REMOTE_DB_USER=coingecko \
   REMOTE_DB_PASSWORD='Coingecko@2025#DB' \
   REMOTE_DB_NAME=timedb \
   ./venv/bin/python src/main.py health --config /databao/datasync/config/datasync.yml
   ```

### 📋 测试清单

在修改任何代码之前，必须确认：

- [ ] 问题在生产环境中真实存在
- [ ] 已检查SystemD服务配置
- [ ] 已检查服务日志
- [ ] 测试方法与生产环境一致
- [ ] 理解了问题的根本原因
- [ ] 不是因为测试方法错误导致的虚假问题

### 💡 经验总结

**重要教训**：
- **不要基于错误的测试方法得出结论**
- **不要修复不存在的问题**
- **总是先检查生产环境的实际运行状态**
- **测试方法必须与实际部署方式一致**

## 🐛 已知问题

### 网络连接警告
**问题**: DataSync出现 "Temporary failure in name resolution" 警告
**影响**: 不影响本地数据库同步，但可能影响远程数据获取
**状态**: 需要检查网络连接和DNS解析

### 端口冲突问题
**问题**: Monitor服务启动时出现 "address already in use" 错误
**原因**: 有手动启动的Monitor进程占用了9527端口
**解决**: 先停止所有旧进程再启动服务
```bash
# 查找占用端口的进程
sudo ss -tlnp | grep 9527
# 停止进程
sudo kill <PID>
# 启动服务
sudo systemctl start databao-monitor
```

### DataView API超时问题 ⚠️ **重要故障排除**
**问题**: Next.js前端出现 "timeout of 10000ms exceeded" 错误
**现象**: 浏览器显示API调用失败，Console显示AxiosError
**根本原因**: 数据库负载过重，特别是DataInsight长时间占用资源

**诊断步骤**:
```bash
# 1. 检查系统负载
top -bn1 | head -15

# 2. 检查数据库连接状态  
PGPASSWORD=datasync2025 psql -h localhost -U datasync -d cryptodb -c \
"SELECT count(*) as active_connections, state FROM pg_stat_activity WHERE state IS NOT NULL GROUP BY state;"

# 3. 检查DataView服务状态
curl -w "响应时间: %{time_total}s\n" -s -o /dev/null http://localhost:8080/api/v1/coins/

# 4. 检查端口监听
ss -tlnp | grep -E ":3000|:8080"
```

**解决方案**:
```bash
# 方案1: 重启所有服务 (推荐)
sudo systemctl stop datasync datainsight databao-monitor
# 等待30秒让数据库清理连接
sleep 30
sudo systemctl start datasync
sudo systemctl start datainsight  
sudo systemctl start databao-monitor

# 方案2: 只重启DataView (快速)
# 结束DataView进程
sudo kill $(sudo lsof -t -i:8080) 2>/dev/null
# 重新启动 (使用上面的启动命令)

# 方案3: 暂时停止DataInsight释放压力
sudo systemctl stop datainsight
# 等待API恢复后再启动DataInsight
```

**预防措施**:
- 监控系统负载，Load Average超过10时需要注意
- 定期检查数据库活跃连接数量
- DataInsight执行期间避免大量API请求

---

**重要提醒**: 
1. 所有Python服务都使用虚拟环境
2. SystemD服务必须配置正确的Python路径
3. 日志目录权限必须正确设置
4. 环境变量必须在服务文件中正确配置

## 📝 变更日志

### 2025-09-20 16:35 - DataView局域网访问配置明确化与React无限循环修复 🌐
- ✅ **问题背景**: 用户报告比特币页面显示"Application error: a client-side exception has occurred"
- ✅ **根因分析**:
  - React组件SWR缓存使用template literal导致无限循环API调用
  - Next.js跨域配置需要明确支持局域网地址192.168.5.124
- ✅ **React无限循环修复**:
  - 修改`/databao/dataview/frontend/src/app/coin/[coin_id]/page.tsx`中SWR缓存key
  - 从template literal改为数组形式: `['coin-history', coinId, params.start, params.end]`
  - 避免每次render创建新字符串对象导致的缓存失效
- ✅ **局域网访问配置明确化**:
  - 更新`next.config.ts`添加详细注释说明192.168.5.124为DataBao专用局域网地址
  - 在`/databao/CLAUDE.md`中添加专门的"🌐 局域网访问配置"章节
  - 创建`/databao/dataview/NETWORK_CONFIG.md`详细说明网络架构和配置
  - 明确所有启动命令使用`--host 0.0.0.0`绑定所有网络接口
- ✅ **服务清理与验证**:
  - 清理重复的后端API进程，启动单一干净的uvicorn实例
  - 验证API连接正常：成功响应比特币数据查询
  - 确认跨域配置生效：支持从192.168.5.124访问前端和API
- ✅ **文档完善**:
  - 明确说明系统不是纯localhost配置，而是专门的局域网访问配置
  - 提供网络故障排除指南和测试命令
  - 标准化访问地址：http://192.168.5.124:3000 (前端) 和 http://192.168.5.124:8080 (API)

### 2025-09-19 15:30 - DataView指标数据显示修复与前端图片服务优化 🎯
- ✅ **问题诊断**: 用户报告首页后三列指标数据全显示为"--"（dash）
- ✅ **根因分析**: 超快API优化后遗留问题，coins.py中缺少indicator_data表的JOIN查询
- ✅ **指标数据修复**:
  - 修改`/databao/dataview/backend/src/api/coins.py`主查询，添加LEFT JOIN indicator_data
  - 使用CASE语句聚合三个关键指标: `CAPITAL_INFLOW_INTENSITY_3M`, `VOLUME_CHANGE_RATIO_3M`, `AVG_VOLUME_3M_24H`
  - 完善数据类型转换，确保指标字段正确处理float类型
- ✅ **前端图片服务优化**:
  - 创建智能`CoinImage`组件，支持后端图片加载失败时自动隐藏
  - 更新`CoinDataTable`和币种详情页使用新的图片组件
  - 移除Next.js配置中的外部图片域名依赖，完全使用本地API
  - 实现图片加载状态管理：loading → success/error → hide
- ✅ **代码清理与架构简化**:
  - 移除冗余的ultra-fast API端点，避免路由冲突
  - 将超快查询逻辑直接集成到主coins端点
  - 统一使用异步数据库连接，避免sync/async混合问题
- ✅ **性能验证**:
  - API响应时间维持在1.2秒左右（相比原来10秒+ 88%优化保持）
  - 指标数据正确显示：资本流入强度、量变比率、平均交易量
  - 图片加载优化，失败时优雅降级不影响页面布局
- ✅ **用户体验改进**:
  - 解决首页"后面三个数据没有展示"问题
  - 图片加载失败不再影响表格显示
  - 保持超快加载速度的同时完整显示所有数据列

### 2025-09-09 04:05 - DataSync网络连接修复与自动重启机制 🔧
- ✅ **问题诊断**: DataSync第二轮查询卡住导致13小时同步滞后
- ✅ **根因分析**: SystemD服务缺少代理环境变量配置
- ✅ **网络修复**: 
  - 添加代理环境变量: `https_proxy`, `http_proxy`, `all_proxy`
  - 修复远程数据库连接问题
  - 恢复110万+积压数据的连续同步
- ✅ **自动重启机制**: 
  - DataSync & DataInsight添加`RuntimeMaxSec=1800`配置
  - 每30分钟系统级自动重启，避免连接积累问题
  - 删除不必要的cron脚本，使用systemd原生机制
- ✅ **效果验证**: 
  - DataSync成功连接远程数据库
  - 检测到1,104,219条待同步记录
  - 追赶机制启动，每批次处理10,000条记录

### 2025-09-07 17:30 - DataInsight 简化版高效调度器最终版 🎉
- ✅ **代码精简**: 从583行代码优化到372行 (减少36%)
- ✅ **架构简化**: 删除复杂的PostgreSQL通知监听、多重降级方案、冗余错误处理
- ✅ **核心功能保留**: 
  - 一次查询9个时间点: `[0, 3, 6, 9, 12, 60, 180, 480, 1440]分钟`
  - 内存计算16个指标: 11个基础指标 + 5个聚合指标
  - 批量保存机制，数据库负载极小
- ✅ **准实时计算机制**: 
  - 每3秒检查新数据 (轻量时间戳查询)
  - 发现新数据后等待5秒确保DataSync写入完成
  - 连续计算所有滞后数据块，追赶速度极快 (每块3秒)
- ✅ **性能表现**: 
  - 第一个数据块: 10秒 (包含发现+等待+计算)
  - 后续数据块: 每块3秒 (连续追赶)
  - 总计算耗时: 约2秒完成45000个指标结果
- ✅ **数据安全**: 以数据库最新时间为准，避免系统时间依赖
- ✅ **并发安全**: 5秒等待机制完全避免DataSync写入冲突

### 2025-09-02 20:56 - DataView API超时问题彻底解决 🎉
- ✅ **问题诊断**: 发现Next.js 15.5.2前端API调用超时10秒 (`timeout of 10000ms exceeded`)
- ✅ **根因分析**: DataInsight长时间占用数据库资源，系统负载过高 (Load Average: 14.53)
- ✅ **系统重启**: 完整重启所有DataBao服务，清理数据库连接积压
- ✅ **API查询优化**: 
  - 添加时间范围限制 `time >= NOW() - INTERVAL '1 day'` 避免全表扫描
  - 减小默认页面大小从100改为50 (测试时使用20)
  - 优化总数查询逻辑，无搜索时使用估算避免COUNT(*)
  - 修复SQL语法错误 (重复ORDER BY子句)
- ✅ **性能突破**: API响应从无限超时改善至14秒可用状态
- ✅ **功能验证**: 成功返回4339个币种数据，分页正常工作
- ✅ **DataView服务配置**:
  - 后端API: `http://localhost:8080` (FastAPI + Uvicorn)
  - 前端Web: `http://localhost:3000` (Next.js 15.5.2 + Turbopack)
  - 正确的启动命令和环境变量配置
- ⚠️ **重要发现**: 数据库负载过重是主要瓶颈，需要监控DataInsight执行频率

### 2025-09-01 21:16 - DataInsight重大性能优化 🚀
- ✅ **实施方案A激进优化** - 内存计算引擎架构
- ✅ **性能突破**: 计算时间从27秒降至3.2秒 (**提升88.1%**)
- ✅ **查询优化**: 数据库查询从32次降至9次 (**减少71.9%**)
- ✅ **架构重构**: 一次读取，内存计算，批量写入
- ✅ **智能回退**: 失败时自动回退到传统计算模式
- ✅ **新增文件**: 
  - `/databao/datainsight/src/core/memory_engine.py` - 内存计算引擎
  - `/databao/datainsight/test_memory_optimization.py` - 性能测试脚本
- ✅ **配置更新**: 添加optimization配置项支持开关控制

### 2025-08-31 22:44 - Monitor服务修复
- ✅ 为Monitor模块创建了虚拟环境 `/databao/monitor/venv/`
- ✅ 安装了所有Python依赖 (FastAPI, Uvicorn, 等)
- ✅ 修复SystemD服务配置，使用虚拟环境Python
- ✅ 解决端口冲突问题，清理残留进程
- ✅ Monitor服务成功启动，可访问 http://localhost:9527/health

### 2025-08-31 22:36
- ✅ 添加完整的项目启动/停止流程
- ✅ 更新进程冲突问题的详细解决方案
- ✅ 更新开发状态，DataInsight已投入生产
- ✅ 添加已知问题和解决方案
- ✅ 添加实时日志查看命令

### 2025-08-31 22:18
- ✅ 同步进度消息改进，显示实际同步时间
- ✅ 修改监控消息格式

---

**重要提醒**: 
1. ⚠️ **启动顺序很重要**: 数据库 → DataSync → DataInsight → Monitor
2. ⚠️ **进程冲突检查**: 启动前务必检查并清理重复进程
3. ⚠️ **端口冲突检查**: Monitor需检9527端口，启动前检查是否被占用
4. ✅ **所有Python服务都使用虚拟环境**
5. ✅ **SystemD服务必须配置正确的Python路径**
6. ✅ **日志目录权限必须正确设置**

## ✅ 全部服务虚拟环境清单
- ✅ **DataSync**: `/databao/datasync/venv/bin/python`
- ✅ **DataInsight**: `/databao/datainsight/venv/bin/python`  
- ✅ **Monitor**: `/databao/monitor/venv/bin/python`
- ✅ **DataView后端**: `/databao/dataview/backend/venv/bin/python`
- 📱 **DataView前端**: Node.js项目，使用npm/yarn管理依赖

*最后更新: 2025-09-02 21:00*  
*维护者: DataBao团队*