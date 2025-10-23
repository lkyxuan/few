import os
import time
import json
import requests
import logging
from datetime import datetime, timezone
from typing import Dict, Any

# 从配置模块导入常量
from config import UTC_8, WEBHOOK_URL


def get_current_time() -> datetime:
    """获取当前UTC+8时间"""
    return datetime.now(UTC_8)


def datetime_to_ms_timestamp(dt: datetime) -> int:
    """将 datetime 转换为毫秒级时间戳（UTC）"""
    # 确保 datetime 是时区感知的，如果不是，则假定为 UTC
    # 这一步对于从 API 解析的含 'Z' (UTC) 的时间字符串是关键的。
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def align_time_to_3min(ms_timestamp: int) -> int:
    """将毫秒时间戳对齐到3分钟间隔"""
    # / 1000 转换为秒，tz=timezone.utc 确保它是时区感知的 UTC 时间
    dt_utc = datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc)

    # 2. 执行对齐逻辑
    minutes = dt_utc.minute
    # 计算应该对齐到的分钟数 (3, 6, 9, 12, ...)
    aligned_minutes = (minutes // 3) * 3

    # 3. 创建对齐后的 datetime 对象
    # 注意：month, day, year 保持不变，只更改 minute, second, microsecond
    aligned_dt = dt_utc.replace(
        minute=aligned_minutes,
        second=0,
        microsecond=0
    )

    # 4. 将对齐后的 datetime 对象转换回毫秒时间戳
    # .timestamp() 返回秒级时间戳 (UTC)，乘以 1000 得到毫秒
    aligned_ms_timestamp = int(aligned_dt.timestamp() * 1000)

    return aligned_ms_timestamp

def send_webhook(message: str, status: str = 'info'):
    """发送 Webhook 通知"""
    if not WEBHOOK_URL:
        logging.warning("WEBHOOK_URL 未配置，跳过发送通知")
        return

    try:
        data = {
            'timestamp': int(time.time()),
            'msg_type': 'text',
            'content': {
                'text': f'[CoinGecko Collector {status.upper()}]\n{message}'
            }
        }
        response = requests.post(WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"发送 Webhook 通知失败: {e}")


def report_status(status: Dict[str, Any], is_error: bool = False):
    """报告采集状态到文件和 Webhook"""
    try:
        status['timestamp'] = int(time.time())
        status['health'] = 'error' if is_error else 'ok'

        # 确保目录存在
        status_dir = '/root/coingecko_fetch'
        os.makedirs(status_dir, exist_ok=True)
        status_file = os.path.join(status_dir, 'status.json')

        with open(status_file, 'w') as f:
            json.dump(status, f)

    except Exception as e:
        logging.error(f"保存状态文件失败: {e}")

    try:
        # 发送 Webhook 通知
        message = (
            f"采集状态报告:\n"
            f"- 采集时间: {datetime.fromtimestamp(status['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- 采集币种数: {status.get('total_coins', 0)}\n"
            f"- 成功页数: {status.get('successful_pages', 0)}\n"
            f"- 失败页数: {status.get('failed_pages', 0)}\n"
            f"- 总耗时: {status.get('total_time', 0):.2f}秒\n"
            f"- 成功率: {status.get('success_rate', 0):.2f}%\n"
            f"- 最小市值: ${status.get('min_market_cap', 0):,.2f}\n"
            f"- 健康状态: {status['health']}"
        )
        if is_error and 'error' in status:
            message += f"\n- 错误信息: {status['error']}"

        send_webhook(message, 'error' if is_error else 'info')
    except Exception as e:
        logging.error(f"发送状态报告 Webhook 失败: {e}")