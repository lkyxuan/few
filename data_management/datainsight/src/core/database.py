#!/usr/bin/env python3
"""
DataInsight数据库管理器
负责所有数据库连接、查询和写入操作
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import asyncpg
from asyncpg.pool import Pool

from .exceptions import (
    DatabaseConnectionError, DatabaseQueryError, DatabaseTimeoutError,
    DataIntegrityError
)


class DatabaseManager:
    """DataInsight数据库管理器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据库管理器
        
        Args:
            db_config: 数据库配置字典
        """
        self.config = db_config['local']
        self.logger = logging.getLogger('datainsight.database')
        self.pool: Optional[Pool] = None
        self._connection_string = self._build_connection_string()
        
        self.logger.info("数据库管理器初始化完成")
    
    def _build_connection_string(self) -> str:
        """构建数据库连接字符串"""
        # 支持环境变量替换
        user = self._resolve_env_var(self.config['user'])
        password = self._resolve_env_var(self.config['password'])
        
        return (
            f"postgresql://{user}:{password}@"
            f"{self.config['host']}:{self.config['port']}"
            f"/{self.config['name']}"
        )
    
    def _resolve_env_var(self, value: str) -> str:
        """解析环境变量"""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.environ.get(env_var, '')
        return value
    
    async def initialize(self):
        """初始化数据库连接池"""
        try:
            # 创建连接池（注意：asyncpg不支持retry参数，需要在应用层处理重试）
            retry_attempts = self.config.get('connection_retry_attempts', 3)
            retry_delay = self.config.get('connection_retry_delay', 1)
            
            for attempt in range(retry_attempts):
                try:
                    self.pool = await asyncpg.create_pool(
                        self._connection_string,
                        min_size=self.config.get('min_pool_size', 5),
                        max_size=self.config.get('pool_size', 50),
                        command_timeout=self.config.get('command_timeout', 45),
                        max_inactive_connection_lifetime=self.config.get('max_inactive_connection_lifetime', 1800),
                        server_settings={
                            'application_name': 'datainsight'
                        }
                    )
                    break  # 成功创建连接池，跳出重试循环
                except Exception as e:
                    if attempt < retry_attempts - 1:  # 如果不是最后一次尝试
                        self.logger.warning(f"连接池创建失败 (尝试 {attempt + 1}/{retry_attempts}): {e}")
                        await asyncio.sleep(retry_delay)
                    else:
                        raise  # 最后一次尝试失败，抛出异常
            
            # 测试连接
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    self.logger.info("✅ 数据库连接池初始化成功")
                else:
                    raise Exception("数据库连接测试失败")
                    
        except asyncio.TimeoutError as e:
            error_msg = f"数据库连接超时: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise DatabaseTimeoutError(error_msg, self._connection_string)
        except asyncpg.PostgresError as e:
            error_msg = f"PostgreSQL错误: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise DatabaseConnectionError(error_msg, self._connection_string)
        except Exception as e:
            error_msg = f"数据库连接池初始化失败: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise DatabaseConnectionError(error_msg, self._connection_string)
    
    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            self.logger.info("数据库连接池已关闭")
    
    async def get_coin_data_at_time(
        self, 
        target_time: datetime, 
        coin_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取指定时间点的coin_data数据
        
        Args:
            target_time: 目标时间
            coin_ids: 指定币种ID列表，None表示所有币种
            
        Returns:
            币种数据列表
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # 构建查询条件
                where_conditions = ["time = $1"]
                params = [target_time]
                
                if coin_ids:
                    placeholders = ', '.join(f'${i+2}' for i in range(len(coin_ids)))
                    where_conditions.append(f"coin_id IN ({placeholders})")
                    params.extend(coin_ids)
                
                # 根据时间范围自动选择分区表查询
                # 使用父表coin_data，PostgreSQL会自动路由到正确的分区
                query = f"""
                    SELECT coin_id, time, current_price as price, market_cap, total_volume as volume_24h
                    FROM coin_data
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY coin_id
                """
                
                rows = await conn.fetch(query, *params)
                
                result = [
                    {
                        'coin_id': row['coin_id'],
                        'time': row['time'],
                        'price': row['price'],
                        'market_cap': row['market_cap'],
                        'volume_24h': row['volume_24h']
                    }
                    for row in rows
                ]
                
                self.logger.debug(f"查询到{len(result)}条币种数据，时间: {target_time}")
                return result
                
        except Exception as e:
            self.logger.error(f"查询coin_data失败: {e}")
            return []
    
    async def get_indicator_data(
        self, 
        indicator_name: str, 
        target_time: datetime, 
        coin_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取指定指标的数据
        
        Args:
            indicator_name: 指标名称
            target_time: 目标时间
            coin_ids: 指定币种ID列表
            
        Returns:
            指标数据列表
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # 构建查询条件
                where_conditions = ["indicator_name = $1", "time = $2"]
                params = [indicator_name, target_time]
                
                if coin_ids:
                    placeholders = ', '.join(f'${i+3}' for i in range(len(coin_ids)))
                    where_conditions.append(f"coin_id IN ({placeholders})")
                    params.extend(coin_ids)
                
                query = f"""
                    SELECT coin_id, time, indicator_name, timeframe, indicator_value
                    FROM indicator_data
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY coin_id
                """
                
                rows = await conn.fetch(query, *params)
                
                result = [
                    {
                        'coin_id': row['coin_id'],
                        'time': row['time'],
                        'indicator_name': row['indicator_name'],
                        'timeframe': row['timeframe'],
                        'indicator_value': row['indicator_value']
                    }
                    for row in rows
                ]
                
                self.logger.debug(f"查询到{len(result)}条指标数据: {indicator_name}，时间: {target_time}")
                return result
                
        except Exception as e:
            self.logger.error(f"查询indicator_data失败: {e}")
            return []
    
    async def get_market_cap_data(
        self, 
        target_time: datetime, 
        coin_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        获取市值数据用于加权计算
        
        Args:
            target_time: 目标时间
            coin_ids: 币种ID列表
            
        Returns:
            市值数据列表
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                placeholders = ', '.join(f'${i+2}' for i in range(len(coin_ids)))
                
                query = f"""
                    SELECT coin_id, market_cap
                    FROM coin_data
                    WHERE time = $1 AND coin_id IN ({placeholders})
                    ORDER BY coin_id
                """
                
                rows = await conn.fetch(query, target_time, *coin_ids)
                
                result = [
                    {
                        'coin_id': row['coin_id'],
                        'market_cap': row['market_cap']
                    }
                    for row in rows
                ]
                
                self.logger.debug(f"查询到{len(result)}条市值数据，时间: {target_time}")
                return result
                
        except Exception as e:
            self.logger.error(f"查询市值数据失败: {e}")
            return []
    
    async def save_indicator_result(
        self,
        time: datetime,
        coin_id: str,
        indicator_name: str,
        timeframe: str,
        value: float
    ) -> bool:
        """
        保存指标计算结果
        
        Args:
            time: 时间戳
            coin_id: 币种ID
            indicator_name: 指标名称
            timeframe: 时间框架
            value: 指标值
            
        Returns:
            保存是否成功
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # 使用 ON CONFLICT 处理重复数据
                query = """
                    INSERT INTO indicator_data (time, coin_id, indicator_name, timeframe, indicator_value)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (time, coin_id, indicator_name, timeframe)
                    DO UPDATE SET 
                        indicator_value = EXCLUDED.indicator_value,
                        created_at = NOW()
                """
                
                await conn.execute(
                    query, 
                    time, coin_id, indicator_name, timeframe, Decimal(str(value))
                )
                
                self.logger.debug(f"保存指标结果: {indicator_name} - {coin_id} - {value:.6f}")
                return True
                
        except Exception as e:
            self.logger.error(f"保存指标结果失败: {e}")
            return False
    
    async def save_indicator_results_batch(
        self, 
        results: List[Dict[str, Any]]
    ) -> int:
        """
        批量保存指标计算结果 - 优化版本使用COPY FROM STDIN
        
        Args:
            results: 结果列表，每个结果包含time, coin_id, indicator_name, timeframe, value
            
        Returns:
            成功保存的数量
        """
        if not self.pool:
            await self.initialize()
        
        if not results:
            return 0
        
        try:
            async with self.pool.acquire() as conn:
                # 方法1: 尝试使用COPY FROM STDIN (最快的批量插入方式)
                try:
                    # 准备COPY数据格式
                    copy_data = []
                    current_time = datetime.now(timezone.utc)
                    
                    for result in results:
                        copy_data.append([
                            result['time'],
                            result['coin_id'],
                            result['indicator_name'],
                            result['timeframe'],
                            Decimal(str(result['value'])),
                            current_time  # created_at
                        ])
                    
                    # 使用COPY批量插入到临时表，然后UPSERT
                    temp_table = f"temp_indicator_batch_{int(time.time() * 1000)}"
                    
                    # 创建临时表
                    await conn.execute(f"""
                        CREATE TEMP TABLE {temp_table} (
                            time TIMESTAMP WITH TIME ZONE,
                            coin_id TEXT,
                            indicator_name TEXT,
                            timeframe TEXT,
                            indicator_value DECIMAL(20,8),
                            created_at TIMESTAMP WITH TIME ZONE
                        )
                    """)
                    
                    # 批量插入到临时表
                    await conn.copy_records_to_table(temp_table, 
                        records=copy_data,
                        columns=['time', 'coin_id', 'indicator_name', 'timeframe', 'indicator_value', 'created_at']
                    )
                    
                    # 从临时表UPSERT到目标表
                    upsert_query = f"""
                        INSERT INTO indicator_data_hot (time, coin_id, indicator_name, timeframe, indicator_value, created_at)
                        SELECT time, coin_id, indicator_name, timeframe, indicator_value, created_at
                        FROM {temp_table}
                        ON CONFLICT (time, coin_id, indicator_name, timeframe)
                        DO UPDATE SET 
                            indicator_value = EXCLUDED.indicator_value,
                            created_at = EXCLUDED.created_at
                    """
                    await conn.execute(upsert_query)
                    
                    # 清理临时表
                    await conn.execute(f"DROP TABLE {temp_table}")
                    
                    self.logger.info(f"🚀 COPY批量保存{len(results)}条指标结果")
                    return len(results)
                    
                except Exception as copy_error:
                    self.logger.warning(f"COPY方式失败，回退到executemany: {copy_error}")
                    
                    # 方法2: 回退到executemany方式
                    query = """
                        INSERT INTO indicator_data_hot (time, coin_id, indicator_name, timeframe, indicator_value, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (time, coin_id, indicator_name, timeframe)
                        DO UPDATE SET 
                            indicator_value = EXCLUDED.indicator_value,
                            created_at = EXCLUDED.created_at
                    """
                    
                    current_time = datetime.now(timezone.utc)
                    batch_data = [
                        (
                            result['time'],
                            result['coin_id'],
                            result['indicator_name'],
                            result['timeframe'],
                            Decimal(str(result['value'])),
                            current_time
                        )
                        for result in results
                    ]
                    
                    await conn.executemany(query, batch_data)
                    
                    self.logger.info(f"⚡ executemany批量保存{len(results)}条指标结果")
                    return len(results)
                
        except Exception as e:
            self.logger.error(f"❌ 批量保存指标结果失败: {e}")
            return 0
    
    async def check_indicator_data_exists(
        self, 
        indicator_name: str, 
        target_time: datetime,
        coin_id: Optional[str] = None
    ) -> bool:
        """
        检查指标数据是否存在
        
        Args:
            indicator_name: 指标名称
            target_time: 目标时间
            coin_id: 币种ID，None表示检查全局指标
            
        Returns:
            数据是否存在
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                if coin_id:
                    query = """
                        SELECT EXISTS(
                            SELECT 1 FROM indicator_data 
                            WHERE indicator_name = $1 AND time = $2 AND coin_id = $3
                        )
                    """
                    exists = await conn.fetchval(query, indicator_name, target_time, coin_id)
                else:
                    # 检查全局指标或任意币种
                    query = """
                        SELECT EXISTS(
                            SELECT 1 FROM indicator_data 
                            WHERE indicator_name = $1 AND time = $2
                        )
                    """
                    exists = await conn.fetchval(query, indicator_name, target_time)
                
                return bool(exists)
                
        except Exception as e:
            self.logger.error(f"检查指标数据存在性失败: {e}")
            return False
    
    async def get_last_indicator_time(self) -> Optional[datetime]:
        """
        获取最后处理的指标时间
        
        Returns:
            最后的指标时间或None
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT MAX(time) FROM indicator_data"
                result = await conn.fetchval(query)
                return result
                
        except Exception as e:
            self.logger.error(f"查询最后指标时间失败: {e}")
            return None
    
    async def check_indicator_data_exists_for_time(self, target_time: datetime) -> bool:
        """
        检查指定时间点是否已存在任何指标数据
        
        Args:
            target_time: 目标时间点
            
        Returns:
            该时间点是否存在指标数据
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT EXISTS(
                        SELECT 1 FROM indicator_data 
                        WHERE time = $1
                    )
                """
                exists = await conn.fetchval(query, target_time)
                return exists
                
        except Exception as e:
            self.logger.error(f"检查时间点 {target_time} 指标数据存在性失败: {e}")
            return False
    
    async def get_latest_coin_data_time(self) -> Optional[datetime]:
        """
        获取最新的coin_data时间
        
        Returns:
            最新的coin_data时间或None
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT MAX(time) FROM coin_data"
                result = await conn.fetchval(query)
                return result
                
        except Exception as e:
            self.logger.error(f"查询最新coin_data时间失败: {e}")
            return None
    
    async def get_earliest_coin_data_time(self) -> Optional[datetime]:
        """
        获取最早的coin_data时间
        
        Returns:
            最早的coin_data时间或None
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT MIN(time) FROM coin_data"
                result = await conn.fetchval(query)
                return result
                
        except Exception as e:
            self.logger.error(f"查询最早coin_data时间失败: {e}")
            return None
    
    async def get_coin_data_time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取coin_data的时间范围
        
        Returns:
            (最早时间, 最新时间) 元组
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT MIN(time), MAX(time) FROM coin_data"
                row = await conn.fetchrow(query)
                return row[0], row[1]
                
        except Exception as e:
            self.logger.error(f"查询coin_data时间范围失败: {e}")
            return None, None
    
    async def get_indicator_data_time_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取indicator_data的时间范围
        
        Returns:
            (最早时间, 最新时间) 元组
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = "SELECT MIN(time), MAX(time) FROM indicator_data"
                row = await conn.fetchrow(query)
                return row[0], row[1]
                
        except Exception as e:
            self.logger.error(f"查询indicator_data时间范围失败: {e}")
            return None, None
    
    async def get_missing_indicator_times(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[datetime]:
        """
        获取指定时间范围内缺失的指标计算时间点
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            缺失的时间点列表
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # 生成3分钟间隔的时间序列
                query = """
                    WITH time_series AS (
                        SELECT generate_series($1, $2, interval '3 minutes') AS time
                    ),
                    existing_times AS (
                        SELECT DISTINCT time 
                        FROM indicator_data 
                        WHERE time BETWEEN $1 AND $2
                    )
                    SELECT ts.time
                    FROM time_series ts
                    LEFT JOIN existing_times et ON ts.time = et.time
                    WHERE et.time IS NULL
                    ORDER BY ts.time
                """
                
                rows = await conn.fetch(query, start_time, end_time)
                result = [row['time'] for row in rows]
                
                self.logger.debug(f"发现{len(result)}个缺失的时间点")
                return result
                
        except Exception as e:
            self.logger.error(f"查询缺失时间点失败: {e}")
            return []
    
    async def get_available_coins(self, target_time: datetime) -> List[str]:
        """
        获取指定时间点可用的币种列表
        
        Args:
            target_time: 目标时间
            
        Returns:
            币种ID列表
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                query = """
                    SELECT DISTINCT coin_id
                    FROM coin_data
                    WHERE time = $1
                    ORDER BY coin_id
                """
                
                rows = await conn.fetch(query, target_time)
                result = [row['coin_id'] for row in rows]
                
                self.logger.debug(f"时间{target_time}可用币种: {len(result)}个")
                return result
                
        except Exception as e:
            self.logger.error(f"查询可用币种失败: {e}")
            return []
    
    async def get_indicator_statistics(self) -> Dict[str, Any]:
        """
        获取指标数据统计信息
        
        Returns:
            统计信息字典
        """
        if not self.pool:
            await self.initialize()
        
        try:
            async with self.pool.acquire() as conn:
                # 总体统计
                total_query = "SELECT COUNT(*) FROM indicator_data"
                total_count = await conn.fetchval(total_query)
                
                # 按指标统计
                indicator_query = """
                    SELECT indicator_name, COUNT(*) as count
                    FROM indicator_data
                    GROUP BY indicator_name
                    ORDER BY count DESC
                """
                indicator_rows = await conn.fetch(indicator_query)
                
                # 时间范围统计
                time_query = """
                    SELECT 
                        MIN(time) as earliest,
                        MAX(time) as latest,
                        COUNT(DISTINCT time) as time_points
                    FROM indicator_data
                """
                time_row = await conn.fetchrow(time_query)
                
                # 币种统计
                coin_query = """
                    SELECT COUNT(DISTINCT coin_id) as unique_coins
                    FROM indicator_data
                """
                unique_coins = await conn.fetchval(coin_query)
                
                return {
                    'total_records': total_count,
                    'unique_coins': unique_coins,
                    'time_points': time_row['time_points'],
                    'earliest_time': time_row['earliest'],
                    'latest_time': time_row['latest'],
                    'indicators': [
                        {
                            'name': row['indicator_name'],
                            'count': row['count']
                        }
                        for row in indicator_rows
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"查询指标统计信息失败: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """
        数据库健康检查
        
        Returns:
            健康状态
        """
        if not self.pool:
            try:
                await self.initialize()
            except:
                return False
        
        try:
            async with self.pool.acquire() as conn:
                # 检查数据库连接
                result = await conn.fetchval("SELECT 1")
                
                # 检查核心表是否存在
                table_check = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'indicator_data'
                    )
                """)
                
                return result == 1 and table_check
                
        except Exception as e:
            self.logger.error(f"数据库健康检查失败: {e}")
            return False
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态信息
        
        Returns:
            连接池状态字典
        """
        if not self.pool:
            return {"status": "not_initialized"}
        
        try:
            return {
                "status": "active",
                "size": self.pool.get_size(),
                "idle_size": self.pool.get_idle_size(),
                "max_size": self.pool.get_max_size(),
                "min_size": self.pool.get_min_size()
            }
        except Exception as e:
            self.logger.error(f"获取连接池状态失败: {e}")
            return {"status": "error", "error": str(e)}
    
    async def cleanup_old_data(self, retention_days: int = 365) -> int:
        """
        清理旧数据 (仅用于开发测试，生产环境应该由数据迁移系统处理)
        
        Args:
            retention_days: 保留天数
            
        Returns:
            删除的记录数
        """
        if not self.pool:
            await self.initialize()
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            async with self.pool.acquire() as conn:
                query = "DELETE FROM indicator_data WHERE created_at < $1"
                result = await conn.execute(query, cutoff_time)
                
                # 从结果字符串中提取删除的行数
                deleted_count = int(result.split()[-1]) if result.startswith('DELETE') else 0
                
                self.logger.info(f"清理了{deleted_count}条旧指标数据")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"清理旧数据失败: {e}")
            return 0