"""
Database models for es-inventory-hub
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, 
    ForeignKey, Index, UniqueConstraint, BigInteger
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SiteAlias(Base):
    """Site aliases to unify Ninja Sites + ThreatLocker Tenants"""
    __tablename__ = 'site_aliases'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    alias_name = Column(String(255), nullable=False)
    alias_type = Column(String(50), nullable=False)  # 'ninja_site' or 'threatlocker_tenant'
    external_id = Column(String(100), nullable=False)  # Original ID from external system
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    site = relationship("Site", back_populates="aliases")
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_site_alias_type_id', 'alias_type', 'external_id'),
        Index('idx_site_alias_site', 'site_id'),
        UniqueConstraint('alias_type', 'external_id', name='uq_site_alias_type_id'),
    )


class Site(Base):
    """Canonical site names that unify Ninja Sites + ThreatLocker Tenants"""
    __tablename__ = 'sites'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", back_populates="site")
    aliases = relationship("SiteAlias", back_populates="site")


class Device(Base):
    """Core device information"""
    __tablename__ = 'devices'
    
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    
    # Device identifiers
    ninja_device_id = Column(String(100), nullable=True, unique=True)
    threatlocker_device_id = Column(String(100), nullable=True, unique=True)
    
    # Device properties
    hostname = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    node_class = Column(String(100), nullable=True)  # For VMWARE_VM_GUEST detection
    
    # Classification
    is_spare = Column(Boolean, default=False)
    is_server = Column(Boolean, default=False)
    is_billable = Column(Boolean, default=True)
    
    # Metadata
    source_system = Column(String(50), nullable=False)  # 'ninja' or 'threatlocker'
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship("Site", back_populates="devices")
    snapshots = relationship("DeviceSnapshot", back_populates="device")
    
    # Indexes
    __table_args__ = (
        Index('idx_device_ninja_id', 'ninja_device_id'),
        Index('idx_device_threatlocker_id', 'threatlocker_device_id'),
        Index('idx_device_site', 'site_id'),
        Index('idx_device_spare', 'is_spare'),
        Index('idx_device_server', 'is_server'),
        Index('idx_device_billable', 'is_billable'),
    )


class DeviceSnapshot(Base):
    """Daily device snapshots with full data payload"""
    __tablename__ = 'device_snapshots'
    
    id = Column(BigInteger, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=False)
    
    # Snapshot metadata
    snapshot_date = Column(DateTime, nullable=False)
    data_hash = Column(String(64), nullable=False)  # SHA256 of full payload
    source_system = Column(String(50), nullable=False)
    
    # Full data payload (JSON)
    ninja_data = Column(Text, nullable=True)  # JSON from NinjaRMM
    threatlocker_data = Column(Text, nullable=True)  # JSON from ThreatLocker
    
    # Common extracted fields for quick access
    hostname = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    node_class = Column(String(100), nullable=True)
    os_name = Column(String(255), nullable=True)
    os_version = Column(String(255), nullable=True)
    last_seen = Column(DateTime, nullable=True)
    
    # Classification (redundant with device but useful for historical tracking)
    is_spare = Column(Boolean, default=False)
    is_server = Column(Boolean, default=False)
    is_billable = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", back_populates="snapshots")
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_snapshot_device_date', 'device_id', 'snapshot_date'),
        Index('idx_snapshot_date', 'snapshot_date'),
        Index('idx_snapshot_hash', 'data_hash'),
        Index('idx_snapshot_source', 'source_system'),
        UniqueConstraint('device_id', 'snapshot_date', 'source_system', name='uq_device_date_source'),
    )


class DailyCounts(Base):
    """Daily rollup counts for quick dashboard access"""
    __tablename__ = 'daily_counts'
    
    id = Column(Integer, primary_key=True)
    count_date = Column(DateTime, nullable=False)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    
    # Device counts by type
    total_devices = Column(Integer, default=0)
    servers = Column(Integer, default=0)
    workstations = Column(Integer, default=0)
    spare_devices = Column(Integer, default=0)
    billable_devices = Column(Integer, default=0)
    
    # Source breakdown
    ninja_devices = Column(Integer, default=0)
    threatlocker_devices = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    site = relationship("Site")
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_daily_counts_date', 'count_date'),
        Index('idx_daily_counts_site', 'site_id'),
        UniqueConstraint('count_date', 'site_id', name='uq_daily_count_date_site'),
    )


class MonthEndCounts(Base):
    """Month-end snapshots for retention policy"""
    __tablename__ = 'month_end_counts'
    
    id = Column(Integer, primary_key=True)
    month_end_date = Column(DateTime, nullable=False)
    site_id = Column(Integer, ForeignKey('sites.id'), nullable=False)
    
    # Device counts by type
    total_devices = Column(Integer, default=0)
    servers = Column(Integer, default=0)
    workstations = Column(Integer, default=0)
    spare_devices = Column(Integer, default=0)
    billable_devices = Column(Integer, default=0)
    
    # Source breakdown
    ninja_devices = Column(Integer, default=0)
    threatlocker_devices = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    site = relationship("Site")
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_month_end_date', 'month_end_date'),
        Index('idx_month_end_site', 'site_id'),
        UniqueConstraint('month_end_date', 'site_id', name='uq_month_end_date_site'),
    )
