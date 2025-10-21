
import os
import time
import logging
import schedule
from typing import Dict, Any

# 导入配置 (确保在日志配置前导入DB_CONFIG以供日志使用)
from config import DB_CONFIG, COINS_PER_PAGE, MAX_RETRIES

# 导入模块
from utils import get_current_time, report_status
from database import get_db_connection, save_to_database
from data_fetcher import fetch_coin_data, verify_batch_data

# --- 日志配置 ---
# 确保日志目录存在
log_dir = os.path.dirname('coingecko_collector.log')
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler('coingecko_collector.log'),
        logging.StreamHandler()
    ]
)


# --- 日志配置结束 ---


def collect_all_data():
    """
    执行一轮完整的数据采集任务。
    """
    logging.info("--- 开始新一轮数据采集 ---")

    # 初始化状态报告
    status: Dict[str, Any] = {
        'total_coins': 0,
        'successful_pages': 0,
        'failed_pages': 0,
        'min_market_cap': float('inf'),
        'last_page': 0
    }
    start_time = time.time()

    try:
        # 获取数据库连接 (在整个采集中使用同一个连接和事务)
        with get_db_connection() as conn:
            current_time = get_current_time()  # 使用相同的时间戳
            page = 1

            while True:
                status['last_page'] = page
                start_rank = (page - 1) * COINS_PER_PAGE + 1
                end_rank = page * COINS_PER_PAGE

                logging.info(f"--- 处理第 {page} 页 (Ranks {start_rank}-{end_rank}) ---")

                page_start_time = time.time()
                data = fetch_coin_data(page)  # fetch_coin_data 内部处理了重试

                if data is None:
                    logging.error(f"第 {page} 页数据获取失败 (已达最大重试次数)")
                    status['failed_pages'] += 1
                    if status['failed_pages'] >= 3:
                        logging.error("连续失败页数过多，本轮采集提前结束")
                        raise Exception("连续3页数据获取失败")
                    page += 1
                    continue  # 尝试下一页

                if not data:
                    logging.info("API返回空数据，已到达最后一页，本轮采集完成")
                    break  # 正常结束

                # 更新最小市值
                market_caps = [coin.get('market_cap', 0) for coin in data if coin.get('market_cap') is not None]
                if market_caps:
                    status['min_market_cap'] = min(status['min_market_cap'], min(market_caps))

                # 验证批次数据
                is_valid, should_stop = verify_batch_data(data, (start_rank, end_rank))

                print(is_valid, should_stop)
                if not is_valid:
                    logging.error(f"第 {page} 页数据验证失败，跳过此页")
                    status['failed_pages'] += 1
                    page += 1
                    continue  # 跳过此页

                # 保存到数据库 (save_to_database 内部处理重试逻辑)
                save_success = False
                for save_attempt in range(MAX_RETRIES):
                    if save_to_database(data, conn, current_time):
                        save_success = True
                        break
                    logging.warning(f"第 {page} 页数据保存失败，第 {save_attempt + 1} 次尝试")
                    time.sleep(2 ** save_attempt)

                if not save_success:
                    logging.error(f"第 {page} 页数据保存失败 (已达最大重试次数)")
                    status['failed_pages'] += 1
                    # 严重错误，可能需要停止
                    raise Exception(f"第 {page} 页数据保存失败")

                status['successful_pages'] += 1
                status['total_coins'] += len(data)

                page_time = time.time() - page_start_time
                logging.info(f"第 {page} 页处理完成，耗时 {page_time:.2f} 秒")

                if should_stop:
                    logging.info(f"触发停止条件 (最小市值 ${status['min_market_cap']:,.2f})，本轮采集完成")
                    break

                page += 1
                time.sleep(1)  # 尊重API速率限制

    except Exception as e:
        logging.error(f"数据采集过程出错: {e}", exc_info=True)
        status['error'] = str(e)
        # 报告失败状态
        total_time = time.time() - start_time
        status['total_time'] = total_time
        if (status['successful_pages'] + status['failed_pages']) > 0:
            status['success_rate'] = status['successful_pages'] / (
                        status['successful_pages'] + status['failed_pages']) * 100
        else:
            status['success_rate'] = 0.0

        report_status(status, is_error=True)
        return  # 发生异常时结束

    # 报告成功状态
    total_time = time.time() - start_time
    status['total_time'] = total_time
    if (status['successful_pages'] + status['failed_pages']) > 0:
        status['success_rate'] = status['successful_pages'] / (
                    status['successful_pages'] + status['failed_pages']) * 100
    else:
        status['success_rate'] = 100.0 if status['successful_pages'] > 0 else 0.0

    report_status(status, is_error=(status['failed_pages'] > 0))
    logging.info(
        f"--- 数据采集完成 ---\n"
        f"总耗时: {total_time:.2f} 秒\n"
        f"总币种数: {status['total_coins']}\n"
        f"成功页数: {status['successful_pages']}\n"
        f"失败页数: {status['failed_pages']}\n"
        f"最小市值: ${status['min_market_cap']:,.2f}"
    )


def main():
    """主函数，设置和运行定时任务"""
    logging.info(f"启动数据采集程序 (时区: UTC+8)")
    logging.info(f"数据库连接配置: {DB_CONFIG['host']}:{DB_CONFIG['port']} (User: {DB_CONFIG['user']})")

    # 设置定时任务，在每小时的0, 3, 6, ..., 57分钟时执行
    for minute in range(0, 60, 3):
        schedule.every().hour.at(f":{minute:02d}").do(collect_all_data)
        logging.info(f"设置定时任务: 每小时{minute:02d}分执行")

    # 立即执行一次以供测试 (可选)
    # logging.info("启动后立即执行一次采集任务...")
    # collect_all_data()

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logging.info("程序被手动停止")
            break
        except Exception as e:
            logging.error(f"调度器主循环出错: {e}", exc_info=True)
            report_status({'error': f"主循环崩溃: {e}"}, is_error=True)
            logging.info("将在60秒后重试主循环...")
            time.sleep(60)


if __name__ == "__main__":
    # collect_all_data()
    main()
