#!/bin/bash

# 基础配置
PROJECT_DIR="/root/pythonTest/few/coingecko_fetch"
PROGRAM_PATH="$PROJECT_DIR/main.py"
LOG_FILE="$PROJECT_DIR/coingecko_collector.log"
DAEMON_LOG="$PROJECT_DIR/daemon.log"
WEBHOOK_URL="https://open.larksuite.com/open-apis/bot/v2/hook/89ec58fd-27e4-43b0-b6dd-82c30e2a65da"
PID_FILE="$PROJECT_DIR/daemon.pid"

# 记录PID
echo $$ > "$PID_FILE"

# 发送飞书通知
send_alert() {
    local message="$1"
    curl -X POST -H "Content-Type: application/json" \
         -d "{\"msg_type\": \"text\", \"content\": {\"text\": \"[CoinGecko数据采集监控] $message\"}}" \
         "$WEBHOOK_URL" >> "$DAEMON_LOG" 2>&1
}

# 加载环境变量
load_env() {
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(cat "$PROJECT_DIR/.env" | grep -v '^#' | xargs)
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 已加载环境变量" >> "$DAEMON_LOG"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 警告：.env 文件不存在，使用默认配置" >> "$DAEMON_LOG"
    fi
}

# 启动程序
start_program() {
    cd "$PROJECT_DIR"
    load_env
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 错误：Python3 未安装" >> "$DAEMON_LOG"
        send_alert "Python3 未安装，程序启动失败"
        return 1
    fi
    
    # 检查依赖是否安装
    if ! python3 -c "import psycopg2, requests, schedule" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 错误：缺少必要的Python依赖" >> "$DAEMON_LOG"
        send_alert "缺少必要的Python依赖，请运行 pip install -r requirements.txt"
        return 1
    fi
    
    nohup python3 "$PROGRAM_PATH" >> "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # 等待5秒检查进程是否存在
    sleep 5
    if ! ps -p $pid > /dev/null; then
        send_alert "程序启动失败，请检查日志"
        return 1
    fi
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 程序启动成功，PID: $pid" >> "$DAEMON_LOG"
    return 0
}

# 清理函数
cleanup() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 守护进程正在停止..." >> "$DAEMON_LOG"
    pkill -f "main.py" > /dev/null 2>&1 || true
    rm -f "$PID_FILE"
    send_alert "守护进程已停止"
    exit 0
}

# 注册清理函数
trap cleanup SIGTERM SIGINT

# 主循环
echo "$(date '+%Y-%m-%d %H:%M:%S') - 守护进程启动" >> "$DAEMON_LOG"

while true; do
    # 检查进程是否存在
    if ! pgrep -f "python3.*main.py" > /dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 程序未运行，正在重启..." >> "$DAEMON_LOG"
        send_alert "程序未运行，正在重启..."
        pkill -f "main.py" > /dev/null 2>&1 || true
        
        if ! start_program; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - 程序重启失败，5分钟后重试" >> "$DAEMON_LOG"
            send_alert "程序重启失败，5分钟后重试"
            sleep 300
            continue
        else
            send_alert "程序重启成功"
        fi
    fi
    
    sleep 30
done 