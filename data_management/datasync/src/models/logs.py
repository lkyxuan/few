#!/usr/bin/env python3
"""
日志数据模型
"""

from sqlalchemy import Column, String, Integer, BIGINT, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP as PG_TIMESTAMP
from datetime import datetime
from .base import Base


class SyncLog(Base):
    """同步日志模型"""
    
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sync_type = Column(String, nullable=False)
    last_sync_time = Column(PG_TIMESTAMP(timezone=True), nullable=False)
    records_synced = Column(BIGINT, default=0)
    sync_status = Column(String, nullable=False, default='completed')
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(PG_TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(PG_TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SyncLog(id={self.id}, type='{self.sync_type}', status='{self.sync_status}', records={self.records_synced})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'sync_type': self.sync_type,
            'last_sync_time': self.last_sync_time,
            'records_synced': self.records_synced,
            'sync_status': self.sync_status,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class CleanupLog(Base):
    """清理日志模型"""
    
    __tablename__ = 'cleanup_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cleanup_time = Column(PG_TIMESTAMP(timezone=True), nullable=False)
    records_deleted = Column(BIGINT, default=0)
    cleanup_status = Column(String, nullable=False, default='completed')
    time_range_start = Column(PG_TIMESTAMP(timezone=True))
    time_range_end = Column(PG_TIMESTAMP(timezone=True))
    error_message = Column(Text)
    created_at = Column(PG_TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CleanupLog(id={self.id}, status='{self.cleanup_status}', records_deleted={self.records_deleted})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'cleanup_time': self.cleanup_time,
            'records_deleted': self.records_deleted,
            'cleanup_status': self.cleanup_status,
            'time_range_start': self.time_range_start,
            'time_range_end': self.time_range_end,
            'error_message': self.error_message,
            'created_at': self.created_at
        }


class MigrationLog(Base):
    """迁移日志模型"""
    
    __tablename__ = 'migration_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    migration_type = Column(String, nullable=False)
    migration_time = Column(PG_TIMESTAMP(timezone=True), nullable=False)
    records_migrated = Column(BIGINT, default=0)
    migration_status = Column(String, nullable=False, default='completed')
    source_partition = Column(String, nullable=False)
    target_partition = Column(String, nullable=False)
    created_at = Column(PG_TIMESTAMP(timezone=True), default=datetime.utcnow)
    
    def __repr__(self):
        return f"<MigrationLog(id={self.id}, type='{self.migration_type}', records_migrated={self.records_migrated})>"
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'migration_type': self.migration_type,
            'migration_time': self.migration_time,
            'records_migrated': self.records_migrated,
            'migration_status': self.migration_status,
            'source_partition': self.source_partition,
            'target_partition': self.target_partition,
            'created_at': self.created_at
        }