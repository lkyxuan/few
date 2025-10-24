#!/bin/bash

# DataSync 服务安装脚本

set -e

echo "=== DataSync 服务安装 ==="

# 检查权限
if [[ $EUID -ne 0 ]]; then
   echo "❌ 此脚本需要root权限运行"
   echo "请使用: sudo $0"
   exit 1
fi

# 项目路径
DATASYNC_DIR="/databao/datasync"
SERVICE_FILE="$DATASYNC_DIR/config/datasync.service"
SYSTEMD_DIR="/etc/systemd/system"

# 检查项目目录
if [ ! -d "$DATASYNC_DIR" ]; then
    echo "❌ DataSync目录不存在: $DATASYNC_DIR"
    exit 1
fi

# 检查服务文件
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ 服务文件不存在: $SERVICE_FILE"
    exit 1
fi

echo "1. 创建datasync用户和组..."
if ! id "datasync" &>/dev/null; then
    useradd --system --shell /bin/false --home /databao/datasync --create-home datasync
    echo "✅ 已创建datasync用户"
else
    echo "✅ datasync用户已存在"
fi

echo "2. 设置目录权限..."
chown -R datasync:datasync $DATASYNC_DIR
chmod 755 $DATASYNC_DIR
chmod +x $DATASYNC_DIR/src/main.py

echo "3. 复制systemd服务文件..."
cp $SERVICE_FILE $SYSTEMD_DIR/datasync.service
echo "✅ 已复制服务文件到 $SYSTEMD_DIR/datasync.service"

echo "4. 重新加载systemd配置..."
systemctl daemon-reload
echo "✅ 已重新加载systemd配置"

echo "5. 启用服务（开机自启）..."
systemctl enable datasync.service
echo "✅ 已启用DataSync服务开机自启"

echo ""
echo "🎉 DataSync服务安装完成！"
echo ""
echo "📋 常用命令:"
echo "   启动服务:   sudo systemctl start datasync"
echo "   停止服务:   sudo systemctl stop datasync"
echo "   重启服务:   sudo systemctl restart datasync"
echo "   查看状态:   sudo systemctl status datasync"
echo "   查看日志:   sudo journalctl -u datasync -f"
echo "   禁用服务:   sudo systemctl disable datasync"
echo ""
echo "⚠️  注意事项:"
echo "   - 请先配置数据库连接信息"
echo "   - 确保PostgreSQL服务正在运行"
echo "   - 检查配置文件: $DATASYNC_DIR/config/datasync.yml"
echo ""
echo "启动服务请运行: sudo systemctl start datasync"