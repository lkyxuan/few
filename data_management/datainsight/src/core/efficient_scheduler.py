#!/usr/bin/env python3
"""
简化版高效调度器 - 零延迟通知模式
"""

import asyncio
import logging
import math
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from collections import defaultdict

from core.database import DatabaseManager
from utils.logger import setup_logger
from utils.monitor_client import DataInsightMonitorClient


class SimpleEfficientScheduler:
    """简化版高效调度器 - 核心功能only"""
    
    # 9个关键时间点（分钟）
    TIMEPOINTS = [0, 3, 6, 9, 12, 60, 180, 480, 1440]
    
    def __init__(self, config_path: str):
        self.logger = setup_logger('datainsight.efficient')
        self.db_manager = None
        self.is_calculating = False
        
        # 监控客户端
        self.monitor_client = DataInsightMonitorClient(
            service_name="datainsight",
            monitor_url="http://localhost:9527"
        )
        
        # 19个指标配置
        self.indicators = {
            'PRICE_CHANGE_3M': {'type': 'price', 'lookback_idx': 1},
            'PRICE_CHANGE_6M': {'type': 'price', 'lookback_idx': 2}, 
            'PRICE_CHANGE_12M': {'type': 'price', 'lookback_idx': 4},
            'PRICE_CHANGE_24H': {'type': 'price', 'lookback_idx': 8},
            'VOLUME_CHANGE_3M': {'type': 'volume', 'lookback_idx': 1},
            'VOLUME_CHANGE_6M': {'type': 'volume', 'lookback_idx': 2},
            'VOLUME_CHANGE_9M': {'type': 'volume', 'lookback_idx': 3},
            'VOLUME_CHANGE_1H': {'type': 'volume', 'lookback_idx': 5},
            'VOLUME_CHANGE_3H': {'type': 'volume', 'lookback_idx': 6},
            'VOLUME_CHANGE_8H': {'type': 'volume', 'lookback_idx': 7},
            'VOLUME_CHANGE_24H': {'type': 'volume', 'lookback_idx': 8},
            # 聚合指标
            'AVG_BTC_ETH': {'type': 'aggregate', 'base': 'PRICE_CHANGE_24H', 'coins': ['bitcoin', 'ethereum']},
            'AVG_BTC_ETH_SOL': {'type': 'aggregate', 'base': 'PRICE_CHANGE_24H', 'coins': ['bitcoin', 'ethereum', 'solana']},
            'WEIGHTED_AVG_BTC_ETH': {'type': 'weighted_aggregate', 'base': 'PRICE_CHANGE_24H', 'coins': ['bitcoin', 'ethereum']},
            'WEIGHTED_AVG_BTC_ETH_SOL': {'type': 'weighted_aggregate', 'base': 'PRICE_CHANGE_24H', 'coins': ['bitcoin', 'ethereum', 'solana']},
            'WEIGHTED_AVG_SOL_ETH_BNB': {'type': 'weighted_aggregate', 'base': 'PRICE_CHANGE_24H', 'coins': ['solana', 'ethereum', 'binancecoin']},
            # 资金流入强度指标
            'CAPITAL_INFLOW_INTENSITY_3M': {'type': 'capital_inflow_intensity', 'base_volume_change': 'VOLUME_CHANGE_3M'},
            # 交易量分析指标
            'AVG_VOLUME_3M_24H': {'type': 'volume_average'},
            'VOLUME_CHANGE_RATIO_3M': {'type': 'volume_ratio'},
            'VOLUME_IMPACT_LOG_RATIO': {'type': 'volume_log_impact'},
        }
        
        self.logger.info(f"简化版高效调度器初始化完成，{len(self.indicators)}个指标")
    
    async def run_daemon(self):
        """运行守护进程 - 简化的轮询模式"""
        self.logger.info("🚀 启动简化版高效调度器")
        
        await self.initialize()
        
        try:
            while True:
                # 检查并连续计算所有滞后数据
                await self._process_all_pending()
                # 短暂等待
                await asyncio.sleep(3)  # 3秒检查一次
                
        except KeyboardInterrupt:
            self.logger.info("收到停止信号")
        except Exception as e:
            self.logger.error(f"守护进程异常: {e}")
        finally:
            if self.db_manager:
                await self.db_manager.close()
    
    async def initialize(self):
        """初始化数据库连接"""
        db_config = {
            'local': {
                'host': 'localhost',
                'port': 5432,
                'name': 'cryptodb',
                'user': 'datasync', 
                'password': 'datasync2025',
                'pool_size': 5
            }
        }
        
        self.db_manager = DatabaseManager(db_config)
        await self.db_manager.initialize()
        self.logger.info("数据库连接初始化完成")
    
    async def _process_all_pending(self):
        """处理所有待计算数据 - 连续计算到最新"""
        calculation_count = 0
        max_calculations = 20
        
        while calculation_count < max_calculations:
            # 检查是否还有数据需要计算
            latest_coin = await self.db_manager.get_latest_coin_data_time()
            latest_indicator = await self.db_manager.get_last_indicator_time()
            
            if not latest_coin or not latest_indicator:
                break
                
            # 下一个时间点
            next_time = latest_indicator + timedelta(minutes=3)
            
            # 如果下一个时间点超过数据库最新数据，停止
            if next_time > latest_coin:
                if calculation_count > 0:
                    self.logger.info(f"✅ 完成连续计算，共处理{calculation_count}个数据块")
                break
            
            # 首次发现新数据时，等待5秒确保DataSync写入完成
            if calculation_count == 0:
                self.logger.info(f"发现新数据 {next_time}，等待5秒确保DataSync写入完成")
                await asyncio.sleep(5)
                
            # 执行计算
            await self.run_indicators()
            calculation_count += 1
            
            # 避免过度占用
            await asyncio.sleep(1)
    
    async def run_indicators(self, priority_range=None, coins=None, target_time=None):
        """执行指标计算"""
        if self.is_calculating:
            return
            
        self.is_calculating = True
        start_time = time.time()
        
        try:
            # 获取计算时间
            calc_time = await self._get_next_time()
            if not calc_time:
                return
            
            # 获取数据
            all_timepoint_data = await self._fetch_all_timepoints(calc_time)
            data_query_time = time.time() - start_time
            
            if not all_timepoint_data:
                return
            
            # 计算指标
            calc_start = time.time()
            all_results = await self._calculate_all_indicators(calc_time, all_timepoint_data)
            calc_time_spent = time.time() - calc_start
            
            # 保存结果
            save_start = time.time()
            if all_results:
                await self._save_all_results(all_results)
            save_time_spent = time.time() - save_start
            
            total_time = time.time() - start_time
            self.logger.info(f"✅ 计算完成: {len(all_results)}个结果，耗时{total_time:.2f}秒")
            
            # 发送成功通知
            await self.monitor_client.emit_event(
                event_type="indicator_calculation_success",
                level="info",
                message=f"✅ 高效指标计算完成：{len(all_results)}个结果，耗时{total_time:.2f}秒",
                details={
                    "calculation_time": calc_time.isoformat(),
                    "results_count": len(all_results),
                    "total_duration": total_time,
                    "scheduler_type": "SimpleEfficientScheduler"
                },
                metrics={
                    "results_count": len(all_results),
                    "duration_seconds": total_time,
                    "throughput_per_second": len(all_results) / max(total_time, 1)
                }
            )
            
        except Exception as e:
            self.logger.error(f"计算异常: {e}")
        finally:
            self.is_calculating = False
    
    async def _get_next_time(self) -> datetime:
        """获取下个计算时间"""
        try:
            latest_coin = await self.db_manager.get_latest_coin_data_time()
            latest_indicator = await self.db_manager.get_last_indicator_time()
            
            if not latest_coin:
                return None
                
            if not latest_indicator:
                # 首次计算
                return latest_coin - timedelta(minutes=3)
            
            # 下一个时间点
            next_time = latest_indicator + timedelta(minutes=3)
            
            if next_time <= latest_coin:
                return next_time
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"获取计算时间失败: {e}")
            return None
    
    async def _fetch_all_timepoints(self, calc_time: datetime) -> Dict[int, Dict[str, Dict]]:
        """获取所有时间点数据"""
        timepoints = []
        for minutes_back in self.TIMEPOINTS:
            timepoints.append(calc_time - timedelta(minutes=minutes_back))
        
        query = """
        SELECT time, coin_id, current_price, total_volume, market_cap
        FROM coin_data 
        WHERE time = ANY($1::timestamp with time zone[])
        AND current_price > 0
        ORDER BY time DESC, coin_id
        """
        
        try:
            async with self.db_manager.pool.acquire() as conn:
                rows = await conn.fetch(query, timepoints)
                
                data_by_timepoint = defaultdict(dict)
                for row in rows:
                    minutes_diff = int((calc_time - row['time']).total_seconds() / 60)
                    if minutes_diff in self.TIMEPOINTS:
                        time_key = self.TIMEPOINTS.index(minutes_diff)
                        data_by_timepoint[time_key][row['coin_id']] = {
                            'price': float(row['current_price']),
                            'volume': float(row['total_volume']) if row['total_volume'] else 0.0,
                            'market_cap': float(row['market_cap']) if row['market_cap'] else 0.0
                        }
                
                self.logger.info(f"✅ 查询获取 {len(timepoints)} 个时间点，{len(rows)} 条记录")
                return dict(data_by_timepoint)
                
        except Exception as e:
            self.logger.error(f"数据查询异常: {e}")
            return {}
    
    async def _calculate_all_indicators(self, calc_time: datetime, timepoint_data: Dict) -> List[Dict]:
        """计算所有指标"""
        all_results = []
        current_data = timepoint_data.get(0, {})
        
        if not current_data:
            return []
        
        # 基础指标
        for indicator_name, config in self.indicators.items():
            if config['type'] in ['price', 'volume']:
                results = self._calculate_change_indicator(indicator_name, config, current_data, timepoint_data)
                all_results.extend([
                    {
                        'time': calc_time,
                        'coin_id': coin_id,
                        'indicator_name': indicator_name,
                        'indicator_value': value,
                        'timeframe': self._get_timeframe(indicator_name)
                    }
                    for coin_id, value in results.items()
                ])
        
        # 聚合指标
        price_24h_results = {}
        for coin_id, value in self._calculate_change_indicator(
            'PRICE_CHANGE_24H', self.indicators['PRICE_CHANGE_24H'], current_data, timepoint_data
        ).items():
            price_24h_results[coin_id] = value
        
        for indicator_name, config in self.indicators.items():
            if config['type'] in ['aggregate', 'weighted_aggregate']:
                result = self._calculate_aggregate_indicator(indicator_name, config, price_24h_results, current_data)
                if result is not None:
                    all_results.append({
                        'time': calc_time,
                        'coin_id': 'GLOBAL',
                        'indicator_name': indicator_name,
                        'indicator_value': result,
                        'timeframe': '24h'
                    })
        
        # 资金流入强度指标
        for indicator_name, config in self.indicators.items():
            if config['type'] == 'capital_inflow_intensity':
                results = self._calculate_capital_inflow_intensity(indicator_name, config, current_data, timepoint_data)
                all_results.extend([
                    {
                        'time': calc_time,
                        'coin_id': coin_id,
                        'indicator_name': indicator_name,
                        'indicator_value': value,
                        'timeframe': '3m'
                    }
                    for coin_id, value in results.items()
                ])
        
        # 交易量分析指标
        for indicator_name, config in self.indicators.items():
            if config['type'] in ['volume_average', 'volume_ratio']:
                results = self._calculate_volume_analysis_indicator(indicator_name, config, current_data, timepoint_data)
                all_results.extend([
                    {
                        'time': calc_time,
                        'coin_id': coin_id,
                        'indicator_name': indicator_name,
                        'indicator_value': value,
                        'timeframe': '3m'
                    }
                    for coin_id, value in results.items()
                ])
        
        return all_results
    
    def _calculate_change_indicator(self, name: str, config: Dict, current_data: Dict, timepoint_data: Dict) -> Dict[str, float]:
        """计算变化指标"""
        lookback_idx = config['lookback_idx']
        old_data = timepoint_data.get(lookback_idx, {})
        field = 'price' if config['type'] == 'price' else 'volume'
        
        results = {}
        for coin_id in current_data:
            if coin_id in old_data:
                current_val = current_data[coin_id][field]
                old_val = old_data[coin_id][field]
                
                if old_val > 0:
                    change_pct = ((current_val - old_val) / old_val) * 100
                    results[coin_id] = change_pct
        
        return results
    
    def _calculate_aggregate_indicator(self, name: str, config: Dict, price_changes: Dict, current_data: Dict) -> float:
        """计算聚合指标"""
        target_coins = config['coins']
        values = []
        weights = []
        
        for coin_id in target_coins:
            if coin_id in price_changes:
                values.append(price_changes[coin_id])
                if config['type'] == 'weighted_aggregate':
                    weight = current_data.get(coin_id, {}).get('market_cap', 0) or 0
                    weights.append(weight)
                else:
                    weights.append(1.0)
        
        if not values:
            return None
        
        if config['type'] == 'weighted_aggregate':
            total_weight = sum(weights)
            if total_weight > 0:
                return sum(v * w for v, w in zip(values, weights)) / total_weight
        
        return sum(values) / len(values)
    
    def _calculate_capital_inflow_intensity(self, name: str, config: Dict, current_data: Dict, timepoint_data: Dict) -> Dict[str, float]:
        """计算资金流入强度指标
        
        公式: (3分钟交易量变化率 × 24小时交易量) ÷ 市值
        """
        results = {}
        
        # 获取3分钟交易量变化率（已有的VOLUME_CHANGE_3M指标数据）
        volume_change_results = self._calculate_change_indicator(
            'VOLUME_CHANGE_3M', self.indicators['VOLUME_CHANGE_3M'], current_data, timepoint_data
        )
        
        for coin_id in current_data:
            if coin_id in volume_change_results:
                # 获取数据
                volume_change_3m = volume_change_results[coin_id]  # 3分钟交易量变化率（%）
                volume_24h = current_data[coin_id]['volume']       # 24小时交易量
                market_cap = current_data[coin_id]['market_cap']   # 市值
                
                # 避免除零错误
                if market_cap > 0 and volume_24h > 0:
                    # 计算资金流入强度
                    # 注意：volume_change_3m是百分比，这里直接使用
                    intensity = (volume_change_3m * volume_24h) / market_cap
                    results[coin_id] = intensity
        
        return results
    
    def _calculate_volume_analysis_indicator(self, name: str, config: Dict, current_data: Dict, timepoint_data: Dict) -> Dict[str, float]:
        """计算交易量分析指标"""
        results = {}
        prev_data = timepoint_data.get(1, {})  # 3分钟前的数据
        
        for coin_id in current_data:
            if config['type'] == 'volume_average':
                # AVG_VOLUME_3M_24H: 24小时平均3分钟交易量
                volume_24h = current_data[coin_id]['volume']
                if volume_24h > 0:
                    avg_volume_3m = volume_24h / 480.0
                    results[coin_id] = avg_volume_3m
            
            elif config['type'] == 'volume_ratio':
                # VOLUME_CHANGE_RATIO_3M: 滑动差分相对于平均的比率
                if coin_id in prev_data:
                    current_volume = current_data[coin_id]['volume']
                    prev_volume = prev_data[coin_id]['volume']
                    
                    if current_volume > 0:
                        delta_volume = current_volume - prev_volume
                        avg_volume_3m = current_volume / 480.0
                        if avg_volume_3m > 0:
                            ratio = delta_volume / avg_volume_3m
                            results[coin_id] = ratio
            
            elif config['type'] == 'volume_log_impact':
                # VOLUME_IMPACT_LOG_RATIO: 交易量变化除以对数市值
                if coin_id in prev_data:
                    current_volume = current_data[coin_id]['volume']
                    prev_volume = prev_data[coin_id]['volume']
                    market_cap = current_data[coin_id]['market_cap']
                    
                    if current_volume > 0 and market_cap > 1:  # 避免对数为负或零
                        delta_volume = current_volume - prev_volume
                        log_market_cap = math.log(market_cap)
                        if log_market_cap > 0:
                            ratio = delta_volume / log_market_cap
                            results[coin_id] = ratio
        
        return results
    
    def _get_timeframe(self, indicator_name: str) -> str:
        """获取时间框架"""
        if '3M' in indicator_name: return '3m'
        elif '6M' in indicator_name: return '6m'
        elif '9M' in indicator_name: return '9m'
        elif '12M' in indicator_name: return '12m'
        elif '1H' in indicator_name: return '1h'
        elif '3H' in indicator_name: return '3h'
        elif '8H' in indicator_name: return '8h'
        else: return '24h'
    
    async def _save_all_results(self, results: List[Dict]):
        """保存结果"""
        if not results:
            return
            
        query = """
        INSERT INTO indicator_data (time, coin_id, indicator_name, timeframe, indicator_value)
        VALUES ($1, $2, $3, $4, $5)
        """
        
        try:
            async with self.db_manager.pool.acquire() as conn:
                await conn.executemany(query, [
                    (r['time'], r['coin_id'], r['indicator_name'], r['timeframe'], r['indicator_value'])
                    for r in results
                ])
            
            self.logger.info(f"✅ 批量保存 {len(results)} 个结果")
            
        except Exception as e:
            self.logger.error(f"保存结果异常: {e}")


# 测试
async def test_simple_scheduler():
    scheduler = SimpleEfficientScheduler("")
    await scheduler.initialize()
    await scheduler.run_indicators()
    await scheduler.db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_simple_scheduler())