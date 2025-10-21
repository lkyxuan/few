#!/bin/bash

# 基础配置
PROGRAM_PATH="/root/coingecko/coingecko_collector.py"
LOG_FILE="/root/coingecko/coingecko_collector.log"
DAEMON_LOG="/root/coingecko/daemon.log"
VENV_PATH="/root/coingecko/venv/bin/activate"
WEBHOOK_URL="https://open.larksuite.com/open-apis/bot/v2/hook/15024cc5-9148-4bf6-81c1-7f7a716715c6"
PID_FILE="/root/coingecko/daemon.pid"

# 记录PID
echo $$ > "$PID_FILE"

# 发送飞书通知
send_alert() {
    local message="$1"
    curl -X POST -H "Content-Type: application/json" \
         -d "{\"msg_type\": \"text\", \"content\": {\"text\": \"[服务器监控] $message\"}}" \
         "$WEBHOOK_URL" >> "$DAEMON_LOG" 2>&1
}

# 加载环境变量
load_env() {
    if [ -f /root/coingecko_fetch/.env ]; then
        export $(cat /root/coingecko_fetch/.env | grep -v '^#' | xargs)
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 已加载环境变量" >> "$DAEMON_LOG"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 警告：.env 文件不存在" >> "$DAEMON_LOG"
    fi
}

# 启动程序
start_program() {
    cd /root/coingecko_fetch
    source $VENV_PATH
    load_env
    nohup python3 $PROGRAM_PATH >> $LOG_FILE 2>&1 &
    local pid=$!
    
    # 等待5秒检查进程是否存在
    sleep 5
    if ! ps -p $pid > /dev/null; then
        send_alert "程序启动失败，请检查日志"
        return 1
    fi
    return 0
}

# 清理函数
cleanup() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 守护进程正在停止..." >> "$DAEMON_LOG"
    pkill -f "coingecko_collector.py" > /dev/null 2>&1 || true
    rm -f "$PID_FILE"
    exit 0
}

# 注册清理函数
trap cleanup SIGTERM SIGINT

# 主循环
echo "$(date '+%Y-%m-%d %H:%M:%S') - 守护进程启动" >> "$DAEMON_LOG"

while true; do
    # 只检查进程是否存在
    if ! pgrep -f "python3.*coingecko_collector.py" > /dev/null; then
        send_alert "程序未运行，正在重启..."
        pkill -f "coingecko_collector.py" > /dev/null 2>&1 || true
        
        if ! start_program; then
            send_alert "程序重启失败"
            sleep 300
            continue
        fi
    fi
    
    sleep 30
done 