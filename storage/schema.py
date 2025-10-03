from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, ForeignKey, 
    UniqueConstraint, Index, CheckConstraint, BigInteger, Boolean, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime

# Create the base class for all models
Base = declarative_base()

# Create metadata instance
metadata = Base.metadata


class Vendor(Base):
    """Vendor table - represents different vendors/suppliers"""
    __tablename__ = 'vendor'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    sites = relationship("Site", back_populates="vendor")
    site_aliases = relationship("SiteAlias", back_populates="vendor")
    device_identities = relationship("DeviceIdentity", back_populates="vendor")
    device_snapshots = relationship("DeviceSnapshot", back_populates="vendor")
    daily_counts = relationship("DailyCounts", back_populates="vendor")
    month_end_counts = relationship("MonthEndCounts", back_populates="vendor")
    change_logs = relationship("ChangeLog", back_populates="vendor")


class DeviceType(Base):
    """Device type table - represents different types of devices"""
    __tablename__ = 'device_type'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    device_snapshots = relationship("DeviceSnapshot", back_populates="device_type")
    daily_counts = relationship("DailyCounts", back_populates="device_type")
    month_end_counts = relationship("MonthEndCounts", back_populates="device_type")


class BillingStatus(Base):
    """Billing status table - represents different billing statuses"""
    __tablename__ = 'billing_status'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    device_snapshots = relationship("DeviceSnapshot", back_populates="billing_status")
    daily_counts = relationship("DailyCounts", back_populates="billing_status")
    month_end_counts = relationship("MonthEndCounts", back_populates="billing_status")


class Site(Base):
    """Site table - represents sites/locations"""
    __tablename__ = 'site'
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    vendor_site_key = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Unique constraint on vendor_id and vendor_site_key
    __table_args__ = (
        UniqueConstraint('vendor_id', 'vendor_site_key', name='uq_site_vendor_site_key'),
        Index('idx_site_vendor_id', 'vendor_id'),
        Index('idx_site_vendor_site_key', 'vendor_site_key'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="sites")
    device_snapshots = relationship("DeviceSnapshot", back_populates="site")
    daily_counts = relationship("DailyCounts", back_populates="site")
    month_end_counts = relationship("MonthEndCounts", back_populates="site")


class SiteAlias(Base):
    """Site alias table - represents alternative names for sites"""
    __tablename__ = 'site_alias'
    
    id = Column(Integer, primary_key=True)
    canonical_name = Column(String(255), nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    vendor_site_key = Column(String(255), nullable=False)
    
    # Unique constraint on vendor_id and vendor_site_key
    __table_args__ = (
        UniqueConstraint('vendor_id', 'vendor_site_key', name='uq_site_alias_vendor_site_key'),
        Index('idx_site_alias_vendor_id', 'vendor_id'),
        Index('idx_site_alias_vendor_site_key', 'vendor_site_key'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="site_aliases")


class DeviceIdentity(Base):
    """Device identity table - represents unique device identifiers"""
    __tablename__ = 'device_identity'
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    vendor_device_key = Column(String(255), nullable=False)
    first_seen_date = Column(Date, nullable=False)
    last_seen_date = Column(Date, nullable=False)
    
    # Unique constraint on vendor_id and vendor_device_key
    __table_args__ = (
        UniqueConstraint('vendor_id', 'vendor_device_key', name='uq_device_identity_vendor_device_key'),
        Index('idx_device_identity_vendor_id', 'vendor_id'),
        Index('idx_device_identity_vendor_device_key', 'vendor_device_key'),
        Index('idx_device_identity_first_seen', 'first_seen_date'),
        Index('idx_device_identity_last_seen', 'last_seen_date'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="device_identities")
    device_snapshots = relationship("DeviceSnapshot", back_populates="device_identity")


class DeviceSnapshot(Base):
    """Device snapshot table - represents device state at a point in time"""
    __tablename__ = 'device_snapshot'
    
    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    device_identity_id = Column(Integer, ForeignKey('device_identity.id'), nullable=False)
    site_id = Column(Integer, ForeignKey('site.id'), nullable=True)
    device_type_id = Column(Integer, ForeignKey('device_type.id'), nullable=True)
    billing_status_id = Column(Integer, ForeignKey('billing_status.id'), nullable=True)
    hostname = Column(String(255), nullable=True)
    os_name = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Core Device Information
    organization_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    device_status = Column(String(100), nullable=True)
    
    # Timestamps
    last_online = Column(TIMESTAMP(timezone=True), nullable=True)
    agent_install_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # ThreatLocker-specific fields
    organization_id = Column(String(255), nullable=True)
    computer_group = Column(String(255), nullable=True)
    security_mode = Column(String(100), nullable=True)
    deny_count_1d = Column(Integer, nullable=True)
    deny_count_3d = Column(Integer, nullable=True)
    deny_count_7d = Column(Integer, nullable=True)
    install_date = Column(TIMESTAMP(timezone=True), nullable=True)
    is_locked_out = Column(Boolean, nullable=True)
    is_isolated = Column(Boolean, nullable=True)
    agent_version = Column(String(100), nullable=True)
    has_checked_in = Column(Boolean, nullable=True)
    
    # TPM and SecureBoot fields (Ninja-specific)
    has_tpm = Column(Boolean, nullable=True)
    tpm_enabled = Column(Boolean, nullable=True)
    tpm_version = Column(String(100), nullable=True)
    secure_boot_available = Column(Boolean, nullable=True)
    secure_boot_enabled = Column(Boolean, nullable=True)
    
    # Hardware Information (Ninja-specific)
    os_architecture = Column(String(100), nullable=True)
    cpu_model = Column(String(255), nullable=True)
    memory_gib = Column(Numeric(10, 2), nullable=True)
    volumes = Column(Text, nullable=True)
    
    # Unique constraint on snapshot_date, vendor_id, and device_identity_id
    __table_args__ = (
        UniqueConstraint('snapshot_date', 'vendor_id', 'device_identity_id', 
                        name='uq_device_snapshot_date_vendor_device'),
        Index('idx_device_snapshot_date', 'snapshot_date'),
        Index('idx_device_snapshot_vendor_id', 'vendor_id'),
        Index('idx_device_snapshot_device_identity_id', 'device_identity_id'),
        Index('idx_device_snapshot_site_id', 'site_id'),
        Index('idx_device_snapshot_device_type_id', 'device_type_id'),
        Index('idx_device_snapshot_billing_status_id', 'billing_status_id'),
        Index('idx_device_snapshot_hostname', 'hostname'),
        Index('idx_device_snapshot_organization_name', 'organization_name'),
        Index('idx_device_snapshot_display_name', 'display_name'),
        Index('idx_device_snapshot_device_status', 'device_status'),
        Index('idx_device_snapshot_last_online', 'last_online'),
        Index('idx_device_snapshot_agent_install_timestamp', 'agent_install_timestamp'),
        # ThreatLocker-specific indexes
        Index('idx_device_snapshot_organization_id', 'organization_id'),
        Index('idx_device_snapshot_computer_group', 'computer_group'),
        Index('idx_device_snapshot_security_mode', 'security_mode'),
        Index('idx_device_snapshot_deny_count_7d', 'deny_count_7d'),
        Index('idx_device_snapshot_install_date', 'install_date'),
        Index('idx_device_snapshot_is_locked_out', 'is_locked_out'),
        Index('idx_device_snapshot_is_isolated', 'is_isolated'),
        # TPM and SecureBoot indexes
        Index('idx_device_snapshot_has_tpm', 'has_tpm'),
        Index('idx_device_snapshot_tpm_enabled', 'tpm_enabled'),
        Index('idx_device_snapshot_tpm_version', 'tpm_version'),
        Index('idx_device_snapshot_secure_boot_available', 'secure_boot_available'),
        Index('idx_device_snapshot_secure_boot_enabled', 'secure_boot_enabled'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="device_snapshots")
    device_identity = relationship("DeviceIdentity", back_populates="device_snapshots")
    site = relationship("Site", back_populates="device_snapshots")
    device_type = relationship("DeviceType", back_populates="device_snapshots")
    billing_status = relationship("BillingStatus", back_populates="device_snapshots")


class DailyCounts(Base):
    """Daily counts table - represents daily device counts by various dimensions"""
    __tablename__ = 'daily_counts'
    
    snapshot_date = Column(Date, nullable=False, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False, primary_key=True)
    site_id = Column(Integer, ForeignKey('site.id'), nullable=True, primary_key=True)
    device_type_id = Column(Integer, ForeignKey('device_type.id'), nullable=True, primary_key=True)
    billing_status_id = Column(Integer, ForeignKey('billing_status.id'), nullable=True, primary_key=True)
    cnt = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        Index('idx_daily_counts_date', 'snapshot_date'),
        Index('idx_daily_counts_vendor_id', 'vendor_id'),
        Index('idx_daily_counts_site_id', 'site_id'),
        Index('idx_daily_counts_device_type_id', 'device_type_id'),
        Index('idx_daily_counts_billing_status_id', 'billing_status_id'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="daily_counts")
    site = relationship("Site", back_populates="daily_counts")
    device_type = relationship("DeviceType", back_populates="daily_counts")
    billing_status = relationship("BillingStatus", back_populates="daily_counts")


class MonthEndCounts(Base):
    """Month end counts table - represents month-end device counts by various dimensions"""
    __tablename__ = 'month_end_counts'
    
    month_end_date = Column(Date, nullable=False, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False, primary_key=True)
    site_id = Column(Integer, ForeignKey('site.id'), nullable=True, primary_key=True)
    device_type_id = Column(Integer, ForeignKey('device_type.id'), nullable=True, primary_key=True)
    billing_status_id = Column(Integer, ForeignKey('billing_status.id'), nullable=True, primary_key=True)
    cnt = Column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        Index('idx_month_end_counts_date', 'month_end_date'),
        Index('idx_month_end_counts_vendor_id', 'vendor_id'),
        Index('idx_month_end_counts_site_id', 'site_id'),
        Index('idx_month_end_counts_device_type_id', 'device_type_id'),
        Index('idx_month_end_counts_billing_status_id', 'billing_status_id'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="month_end_counts")
    site = relationship("Site", back_populates="month_end_counts")
    device_type = relationship("DeviceType", back_populates="month_end_counts")
    billing_status = relationship("BillingStatus", back_populates="month_end_counts")


class ChangeLog(Base):
    """Change log table - represents changes in metrics over time"""
    __tablename__ = 'change_log'
    
    change_date = Column(Date, nullable=False, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False, primary_key=True)
    metric = Column(Text, nullable=False, primary_key=True)
    prev_value = Column(Integer, nullable=True)
    new_value = Column(Integer, nullable=True)
    delta = Column(Integer, nullable=True)
    details = Column(JSONB, nullable=True)
    
    __table_args__ = (
        Index('idx_change_log_date', 'change_date'),
        Index('idx_change_log_vendor_id', 'vendor_id'),
        Index('idx_change_log_metric', 'metric'),
    )
    
    # Relationships
    vendor = relationship("Vendor", back_populates="change_logs")


class JobRuns(Base):
    """Job runs table - represents job execution history"""
    __tablename__ = 'job_runs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(Text, nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(Text, nullable=False)  # 'running', 'completed', 'failed'
    message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_job_runs_job_name', 'job_name'),
        Index('idx_job_runs_started_at', 'started_at'),
        Index('idx_job_runs_status', 'status'),
    )


class Exceptions(Base):
    """Exceptions table - persistent storage for cross-vendor checks and anomalies"""
    __tablename__ = 'exceptions'
    
    id = Column(BigInteger, primary_key=True)
    date_found = Column(Date, nullable=False, default=datetime.utcnow().date())
    type = Column(String(64), nullable=False)  # e.g. MISSING_NINJA, DUPLICATE_TL, SITE_MISMATCH, SPARE_MISMATCH
    hostname = Column(String(255), nullable=False)
    details = Column(JSONB, nullable=False, default={})
    resolved = Column(Boolean, nullable=False, default=False)
    
    __table_args__ = (
        Index('ix_exceptions_type_date', 'type', 'date_found'),
        Index('ix_exceptions_hostname', 'hostname'),
        Index('ix_exceptions_resolved', 'resolved'),
    )
