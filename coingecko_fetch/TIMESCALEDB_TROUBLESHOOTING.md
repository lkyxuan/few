# TimescaleDB 安装故障排除指南

## 错误信息
```
ERROR: extension "timescaledb" has no installation script nor update path for version "2.19.3"
```

## 问题原因
这个错误通常表示：
1. TimescaleDB 扩展未正确安装
2. PostgreSQL 配置文件中缺少必要的设置
3. PostgreSQL 版本与 TimescaleDB 版本不兼容

## 已解决的问题 ✓

**问题原因：** 
- PostgreSQL 期望 TimescaleDB 版本 2.19.3，但系统实际安装的是 2.17.2
- 代码已修改为自动尝试多个已安装的版本，直到找到可用的版本

**解决方法：**
- 修改了 `init_timescaledb.py`，添加了智能版本检测
- 代码会自动回退到标准 PostgreSQL 表（如果 TimescaleDB 完全不可用）
- 已成功使用 TimescaleDB 2.17.2 版本创建扩展

## 解决方案（其他情况）

### 1. 检查 PostgreSQL 版本
```bash
psql --version
```

### 2. 检查是否已安装 TimescaleDB
```bash
# 检查系统是否安装了 timescaledb
dpkg -l | grep timescaledb
# 或
rpm -qa | grep timescaledb
```

### 3. 安装 TimescaleDB（如果未安装）

#### Ubuntu/Debian 系统：
```bash
# 添加 TimescaleDB 的 APT 仓库
sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"

# 添加 GPG 密钥
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | apt-key add -

# 更新并安装
apt-get update
apt-get install timescaledb-2-postgresql-16  # 根据你的 PostgreSQL 版本调整

# 重启 PostgreSQL
systemctl restart postgresql
```

#### CentOS/RHEL 系统：
```bash
# 添加 TimescaleDB 的 YUM 仓库
yum install -y https://download.postgresql.org/pub/repos/yum/reporpms/EL-8-x86_64/pgdg-redhat-repo-latest.noarch.rpm

# 安装 TimescaleDB
yum install -y timescaledb-2-postgresql-16  # 根据你的 PostgreSQL 版本调整

# 重启 PostgreSQL
systemctl restart postgresql
```

### 4. 配置 PostgreSQL

编辑 PostgreSQL 配置文件（通常在 `/etc/postgresql/[version]/main/postgresql.conf`）：

```bash
# 找到 postgresql.conf 文件位置
psql -U postgres -c "SHOW config_file;"
```

在配置文件中添加或修改以下设置：
```ini
shared_preload_libraries = 'timescaledb'
```

### 5. 重启 PostgreSQL 服务
```bash
systemctl restart postgresql
```

### 6. 在数据库中创建扩展

使用项目中的初始化脚本：
```bash
python init_timescaledb.py
```

或者手动创建：
```bash
psql -U postgres -d test -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
```

### 7. 验证安装

检查扩展是否正确安装：
```bash
psql -U postgres -d test -c "SELECT * FROM pg_extension WHERE extname = 'timescaledb';"
```

## 替代方案：修改代码以禁用 TimescaleDB

如果你暂时无法安装 TimescaleDB，可以修改代码使其不依赖 TimescaleDB 扩展：

### 修改 `init_timescaledb.py`

将第 59 行的扩展创建语句改为使用 try-except：

```python
# 启用TimescaleDB扩展
logging.info("正在启用 TimescaleDB 扩展...")
try:
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
except psycopg2.OperationalError as e:
    logging.warning(f"无法创建 TimescaleDB 扩展，将使用标准 PostgreSQL 表: {e}")
    # 继续创建表，但不转换为超表
else:
    # 创建主数据表...
    # ...
    
    # 将表转换为超表 (hypertable)
    logging.info("正在将 'coin_data' 转换为超表...")
    try:
        cur.execute("""
            SELECT create_hypertable('coin_data', 'time',
                if_not_exists => TRUE,
                migrate_data => TRUE
            );
        """)
    except psycopg2.OperationalError as e:
        logging.warning(f"无法创建超表，将使用标准表: {e}")
```

### 注意事项
- 标准 PostgreSQL 表不支持 TimescaleDB 的时间分区优化
- 查询性能可能会降低
- 建议尽快安装 TimescaleDB 以获得最佳性能

## 需要帮助？

如果上述步骤未能解决问题，请提供以下信息：
1. PostgreSQL 版本：`psql --version`
2. 操作系统版本：`cat /etc/os-release`
3. TimescaleDB 是否已安装：`dpkg -l | grep timescaledb` 或 `rpm -qa | grep timescaledb`
4. 完整的错误日志

