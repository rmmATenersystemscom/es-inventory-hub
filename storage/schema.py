from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, ForeignKey,
    UniqueConstraint, Index, CheckConstraint, BigInteger, Boolean, Numeric,
    text
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

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
    
    # NinjaRMM Modal Fields (for Windows 11 24H2 API)
    location_name = Column(String(255), nullable=True)
    device_type_name = Column(String(100), nullable=True)
    billable_status_name = Column(String(100), nullable=True)
    
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

    # NinjaRMM Node Class (for BHAG/seat calculation)
    node_class = Column(String(100), nullable=True)
    
    # Windows 11 24H2 Assessment fields
    windows_11_24h2_capable = Column(Boolean, nullable=True)
    windows_11_24h2_deficiencies = Column(Text, nullable=True)
    os_build = Column(String(100), nullable=True)
    os_release_id = Column(String(100), nullable=True)
    cpu_model = Column(String(255), nullable=True)
    system_manufacturer = Column(String(255), nullable=True)
    system_model = Column(String(255), nullable=True)
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
        # NinjaRMM Modal Field indexes
        Index('idx_device_snapshot_location_name', 'location_name'),
        Index('idx_device_snapshot_device_type_name', 'device_type_name'),
        Index('idx_device_snapshot_billable_status_name', 'billable_status_name'),
        # NinjaRMM Node Class index
        Index('idx_device_snapshot_node_class', 'node_class'),
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


class JobBatches(Base):
    """Job batches table - represents batch execution tracking"""
    __tablename__ = 'job_batches'
    
    batch_id = Column(String(50), primary_key=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default='queued')
    priority = Column(String(20), nullable=False, default='normal')
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    progress_percent = Column(Integer, nullable=True)
    estimated_completion = Column(TIMESTAMP(timezone=True), nullable=True)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    __table_args__ = (
        Index('idx_job_batches_status', 'status'),
        Index('idx_job_batches_created_at', 'created_at'),
    )


class JobRuns(Base):
    """Job runs table - represents job execution history"""
    __tablename__ = 'job_runs'
    
    job_id = Column(String(50), primary_key=True)
    batch_id = Column(String(50), ForeignKey('job_batches.batch_id'), nullable=True)
    job_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default='queued')
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    progress_percent = Column(Integer, nullable=True)
    message = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Foreign key relationship
    batch = relationship("JobBatches", backref="job_runs")
    
    __table_args__ = (
        Index('idx_job_runs_batch_id', 'batch_id'),
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


# QBR (Quarterly Business Review) Tables

class Organization(Base):
    """Organization table - represents organizations for QBR tracking"""
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    qbr_metrics_monthly = relationship("QBRMetricsMonthly", back_populates="organization")
    qbr_metrics_quarterly = relationship("QBRMetricsQuarterly", back_populates="organization")
    qbr_smartnumbers = relationship("QBRSmartNumbers", back_populates="organization")
    qbr_thresholds = relationship("QBRThresholds", back_populates="organization")


class QBRMetricsMonthly(Base):
    """QBR Monthly Metrics table - stores monthly business metrics"""
    __tablename__ = 'qbr_metrics_monthly'

    id = Column(Integer, primary_key=True)
    period = Column(String(7), nullable=False)  # YYYY-MM format
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Numeric(12, 2), nullable=True)
    data_source = Column(String(20), nullable=False, server_default='collected')  # 'collected' or 'manual'
    collected_at = Column(TIMESTAMP(timezone=True), nullable=True)
    manually_entered_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    organization = relationship("Organization", back_populates="qbr_metrics_monthly")
    vendor = relationship("Vendor")

    __table_args__ = (
        UniqueConstraint('period', 'metric_name', 'organization_id', 'vendor_id',
                        name='uq_metrics_monthly_period_metric_org_vendor'),
        Index('idx_qbr_metrics_monthly_period', 'period'),
        Index('idx_qbr_metrics_monthly_metric_name', 'metric_name'),
        Index('idx_qbr_metrics_monthly_org_id', 'organization_id'),
        Index('idx_qbr_metrics_monthly_vendor_id', 'vendor_id'),
        Index('idx_qbr_metrics_monthly_period_metric', 'period', 'metric_name'),
        Index('idx_qbr_metrics_monthly_data_source', 'data_source'),
    )


class QBRMetricsQuarterly(Base):
    """QBR Quarterly Metrics table - stores quarterly aggregated metrics"""
    __tablename__ = 'qbr_metrics_quarterly'

    id = Column(Integer, primary_key=True)
    period = Column(String(7), nullable=False)  # YYYY-QN format (e.g., "2025-Q1")
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Numeric(12, 2), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    organization = relationship("Organization", back_populates="qbr_metrics_quarterly")

    __table_args__ = (
        UniqueConstraint('period', 'metric_name', 'organization_id',
                        name='uq_metrics_quarterly_period_metric_org'),
        Index('idx_qbr_metrics_quarterly_period', 'period'),
        Index('idx_qbr_metrics_quarterly_metric_name', 'metric_name'),
        Index('idx_qbr_metrics_quarterly_org_id', 'organization_id'),
    )


class QBRSmartNumbers(Base):
    """QBR SmartNumbers table - stores calculated KPIs"""
    __tablename__ = 'qbr_smartnumbers'

    id = Column(Integer, primary_key=True)
    period = Column(String(7), nullable=False)  # YYYY-MM or YYYY-QN format
    period_type = Column(String(20), nullable=False)  # 'monthly' or 'quarterly'
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    kpi_name = Column(String(100), nullable=False)
    kpi_value = Column(Numeric(12, 4), nullable=True)  # Higher precision for ratios
    calculation_method = Column(String(200), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    organization = relationship("Organization", back_populates="qbr_smartnumbers")

    __table_args__ = (
        UniqueConstraint('period', 'kpi_name', 'organization_id',
                        name='uq_smartnumbers_period_kpi_org'),
        Index('idx_qbr_smartnumbers_period', 'period'),
        Index('idx_qbr_smartnumbers_kpi_name', 'kpi_name'),
        Index('idx_qbr_smartnumbers_org_id', 'organization_id'),
    )


class QBRThresholds(Base):
    """QBR Thresholds table - stores alert thresholds for metrics"""
    __tablename__ = 'qbr_thresholds'

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    metric_name = Column(String(100), nullable=False)
    green_min = Column(Numeric(12, 4), nullable=True)  # Green zone minimum
    green_max = Column(Numeric(12, 4), nullable=True)  # Green zone maximum
    yellow_min = Column(Numeric(12, 4), nullable=True)  # Yellow zone minimum
    yellow_max = Column(Numeric(12, 4), nullable=True)  # Yellow zone maximum
    red_threshold = Column(Numeric(12, 4), nullable=True)  # Red zone threshold
    notes = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    organization = relationship("Organization", back_populates="qbr_thresholds")

    __table_args__ = (
        UniqueConstraint('metric_name', 'organization_id',
                        name='uq_thresholds_metric_org'),
        Index('idx_qbr_thresholds_metric_name', 'metric_name'),
        Index('idx_qbr_thresholds_org_id', 'organization_id'),
    )


class QBRCollectionLog(Base):
    """QBR Collection Log table - tracks collection execution history"""
    __tablename__ = 'qbr_collection_log'

    id = Column(Integer, primary_key=True)
    collection_started_at = Column(TIMESTAMP(timezone=True), nullable=False)
    collection_ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    period = Column(String(7), nullable=False)  # YYYY-MM format
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=True)
    status = Column(String(20), nullable=False)  # 'running', 'completed', 'failed'
    error_message = Column(Text, nullable=True)
    metrics_collected = Column(Integer, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    vendor = relationship("Vendor")

    __table_args__ = (
        Index('idx_qbr_collection_log_started_at', 'collection_started_at'),
        Index('idx_qbr_collection_log_period', 'period'),
        Index('idx_qbr_collection_log_vendor_id', 'vendor_id'),
        Index('idx_qbr_collection_log_status', 'status'),
    )


class QBRClientMetrics(Base):
    """QBR Client Metrics table - stores per-client historical seat/endpoint data"""
    __tablename__ = 'qbr_client_metrics'

    id = Column(Integer, primary_key=True)
    period = Column(String(7), nullable=False)  # YYYY-MM format
    client_name = Column(String(255), nullable=False)
    seats = Column(Integer, nullable=True)
    endpoints = Column(Integer, nullable=True)
    data_source = Column(String(20), nullable=False, server_default='imported')  # 'imported' or 'collected'
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('period', 'client_name', name='uq_qbr_client_metrics_period_client'),
        Index('idx_qbr_client_metrics_period', 'period'),
        Index('idx_qbr_client_metrics_client_name', 'client_name'),
    )


# Vendor-specific snapshot tables (non-device data)

class VadeSecureSnapshot(Base):
    """VadeSecure snapshot table - stores daily customer/license data"""
    __tablename__ = 'vadesecure_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    customer_id = Column(String(255), nullable=False)  # vendor_device_key equivalent
    customer_name = Column(String(255), nullable=True)
    company_domain = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)

    # License info
    license_id = Column(String(255), nullable=True)
    product_type = Column(String(100), nullable=True)
    license_status = Column(String(50), nullable=True)  # active, expired
    license_start_date = Column(Date, nullable=True)
    license_end_date = Column(Date, nullable=True)
    tenant_id = Column(String(255), nullable=True)

    # Usage metrics
    usage_count = Column(Integer, nullable=True)  # actual user activity

    # Customer contact/location info
    migrated = Column(Boolean, nullable=True)
    created_date = Column(DateTime, nullable=True)  # ctime from API
    contact_name = Column(String(255), nullable=True)  # firstname + lastname
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'customer_id', name='uq_vadesecure_snapshot_date_customer'),
        Index('idx_vadesecure_snapshot_date', 'snapshot_date'),
        Index('idx_vadesecure_snapshot_customer_id', 'customer_id'),
        Index('idx_vadesecure_snapshot_customer_name', 'customer_name'),
        Index('idx_vadesecure_snapshot_license_status', 'license_status'),
    )


class DropsuiteSnapshot(Base):
    """Dropsuite snapshot table - stores daily email backup/archiving data"""
    __tablename__ = 'dropsuite_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    user_id = Column(String(255), nullable=False)  # Dropsuite user/org ID
    organization_name = Column(String(255), nullable=True)
    seats_used = Column(Integer, nullable=True)
    archive_type = Column(String(50), nullable=True)  # Archive, Backup Only
    status = Column(String(50), nullable=True)  # Active, Deactivated, Suspended
    total_emails = Column(Integer, nullable=True)
    storage_gb = Column(Numeric(10, 2), nullable=True)
    last_backup = Column(TIMESTAMP(timezone=True), nullable=True)
    compliance = Column(Boolean, nullable=True)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'user_id', name='uq_dropsuite_snapshot_date_user'),
        Index('idx_dropsuite_snapshot_date', 'snapshot_date'),
        Index('idx_dropsuite_snapshot_user_id', 'user_id'),
        Index('idx_dropsuite_snapshot_org_name', 'organization_name'),
        Index('idx_dropsuite_snapshot_status', 'status'),
    )


class DuoSnapshot(Base):
    """Duo MFA snapshot table - stores daily MFA account data"""
    __tablename__ = 'duo_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    account_id = Column(String(255), nullable=False)  # Duo account ID
    organization_name = Column(String(255), nullable=True)
    user_count = Column(Integer, nullable=True)
    admin_count = Column(Integer, nullable=True)
    integration_count = Column(Integer, nullable=True)
    phone_count = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True)  # active, inactive, suspended
    last_activity = Column(TIMESTAMP(timezone=True), nullable=True)
    group_count = Column(Integer, nullable=True)
    webauthn_count = Column(Integer, nullable=True)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    enrollment_pct = Column(Numeric(5, 2), nullable=True)  # Percentage of enrolled users
    auth_methods = Column(JSONB, nullable=True)  # Array of enabled auth methods
    directory_sync = Column(Boolean, nullable=True)
    telephony_credits = Column(Integer, nullable=True)  # Credits used in period
    auth_volume = Column(Integer, nullable=True)  # Auth count in last 24h
    failed_auth_pct = Column(Numeric(5, 2), nullable=True)  # Failed auth percentage
    peak_usage = Column(String(50), nullable=True)  # Peak hour range
    account_type = Column(String(100), nullable=True)  # Edition type

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'account_id', name='uq_duo_snapshot_date_account'),
        Index('idx_duo_snapshot_date', 'snapshot_date'),
        Index('idx_duo_snapshot_account_id', 'account_id'),
        Index('idx_duo_snapshot_org_name', 'organization_name'),
        Index('idx_duo_snapshot_status', 'status'),
    )


class DuoUserSnapshot(Base):
    """Duo user snapshot table - stores daily per-user MFA data"""
    __tablename__ = 'duo_user_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    account_id = Column(String(255), nullable=False)  # Duo account ID
    organization_name = Column(String(255), nullable=True)
    user_id = Column(String(255), nullable=False)  # Duo user ID
    username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)  # active, bypass, disabled, locked out
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    phone = Column(String(50), nullable=True)  # Primary phone number
    is_enrolled = Column(Boolean, nullable=True)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'account_id', 'user_id', name='uq_duo_user_snapshot_date_account_user'),
        Index('idx_duo_user_snapshot_date', 'snapshot_date'),
        Index('idx_duo_user_snapshot_account_id', 'account_id'),
        Index('idx_duo_user_snapshot_user_id', 'user_id'),
        Index('idx_duo_user_snapshot_org_name', 'organization_name'),
    )


class M365Snapshot(Base):
    """Microsoft 365 snapshot table - stores daily user/license data per tenant"""
    __tablename__ = 'm365_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    tenant_id = Column(String(255), nullable=False)  # Azure tenant ID
    organization_name = Column(String(255), nullable=True)
    user_count = Column(Integer, nullable=True)  # Filtered user count

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'tenant_id', name='uq_m365_snapshot_date_tenant'),
        Index('idx_m365_snapshot_date', 'snapshot_date'),
        Index('idx_m365_snapshot_tenant_id', 'tenant_id'),
        Index('idx_m365_snapshot_org_name', 'organization_name'),
    )


class M365UserSnapshot(Base):
    """Microsoft 365 user snapshot table - stores daily per-user license data"""
    __tablename__ = 'm365_user_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    tenant_id = Column(String(255), nullable=False)  # Azure tenant ID
    organization_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=False)  # userPrincipalName
    display_name = Column(String(255), nullable=True)
    licenses = Column(Text, nullable=True)  # Comma-separated license names

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'tenant_id', 'username', name='uq_m365_user_snapshot_date_tenant_user'),
        Index('idx_m365_user_snapshot_date', 'snapshot_date'),
        Index('idx_m365_user_snapshot_tenant_id', 'tenant_id'),
        Index('idx_m365_user_snapshot_org_name', 'organization_name'),
        Index('idx_m365_user_snapshot_username', 'username'),
    )


class M365ESUserConfig(Base):
    """M365 ES User definition configuration per organization.

    Stores which definition of 'ES User' applies to each organization:
    - Definition 1: Users with a functioning email mailbox (Exchange license)
    - Definition 2: All M365 users with any paid M365 license
    """
    __tablename__ = 'm365_es_user_config'

    organization_name = Column(String(255), primary_key=True)
    es_user_definition = Column(Integer, nullable=False, default=1)  # 1=email, 2=all licensed
    needs_review = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=text('CURRENT_TIMESTAMP'))

    __table_args__ = (
        Index('idx_m365_es_user_config_definition', 'es_user_definition'),
        Index('idx_m365_es_user_config_needs_review', 'needs_review'),
    )


class VeeamSnapshot(Base):
    """Veeam VSPC snapshot table - stores daily cloud storage usage per organization"""
    __tablename__ = 'veeam_snapshot'

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False)
    company_uid = Column(String(255), nullable=False)  # VSPC company UID
    organization_name = Column(String(255), nullable=True)
    storage_gb = Column(Numeric(12, 2), nullable=True)  # Cloud storage used in GB
    quota_gb = Column(Numeric(12, 2), nullable=True)  # Storage quota in GB
    usage_pct = Column(Numeric(5, 1), nullable=True)  # Usage percentage

    # Metadata
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    __table_args__ = (
        UniqueConstraint('snapshot_date', 'company_uid', name='uq_veeam_snapshot_date_company'),
        Index('idx_veeam_snapshot_date', 'snapshot_date'),
        Index('idx_veeam_snapshot_company_uid', 'company_uid'),
        Index('idx_veeam_snapshot_org_name', 'organization_name'),
    )


# ============================================================================
# TenantSweep Tables - M365 Security Audit Results
# ============================================================================

class TenantSweepAudit(Base):
    """TenantSweep audit table - stores M365 tenant security audit run metadata"""
    __tablename__ = 'tenant_sweep_audits'

    id = Column(Integer, primary_key=True)
    tenant_name = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False)  # Azure AD tenant ID (GUID)
    status = Column(String(50), nullable=False, server_default='running')  # running, completed, failed
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    summary = Column(JSONB, nullable=True)  # Counts per severity: {"Critical": 1, "High": 2, ...}
    error_message = Column(Text, nullable=True)
    initiated_by = Column(String(255), nullable=True)  # User email who ran audit
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    findings = relationship("TenantSweepFinding", back_populates="audit", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_tenant_sweep_audits_tenant_name', 'tenant_name'),
        Index('idx_tenant_sweep_audits_tenant_id', 'tenant_id'),
        Index('idx_tenant_sweep_audits_status', 'status'),
        Index('idx_tenant_sweep_audits_started_at', 'started_at'),
        CheckConstraint("status IN ('running', 'completed', 'failed')", name='chk_tenant_sweep_audit_status'),
    )


class TenantSweepFinding(Base):
    """TenantSweep finding table - stores individual security check results"""
    __tablename__ = 'tenant_sweep_findings'

    id = Column(Integer, primary_key=True)
    audit_id = Column(Integer, ForeignKey('tenant_sweep_audits.id', ondelete='CASCADE'), nullable=False)
    check_id = Column(String(100), nullable=False)  # e.g., 'MFA_ENFORCEMENT'
    check_name = Column(String(255), nullable=False)  # Human-readable name
    severity = Column(String(20), nullable=False)  # Critical, High, Medium, Low, Info
    status = Column(String(50), nullable=False)  # pass, fail, warning, error
    current_value = Column(Text, nullable=True)  # What was found
    expected_value = Column(Text, nullable=True)  # What's recommended
    details = Column(JSONB, nullable=True)  # Additional context
    recommendation = Column(Text, nullable=True)  # Remediation guidance
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    audit = relationship("TenantSweepAudit", back_populates="findings")

    __table_args__ = (
        Index('idx_tenant_sweep_findings_audit_id', 'audit_id'),
        Index('idx_tenant_sweep_findings_check_id', 'check_id'),
        Index('idx_tenant_sweep_findings_severity', 'severity'),
        Index('idx_tenant_sweep_findings_status', 'status'),
        Index('idx_tenant_sweep_findings_audit_severity', 'audit_id', 'severity'),
        CheckConstraint("severity IN ('Critical', 'High', 'Medium', 'Low', 'Info')", name='chk_tenant_sweep_finding_severity'),
        CheckConstraint("status IN ('pass', 'fail', 'warning', 'error')", name='chk_tenant_sweep_finding_status'),
    )


# ============================================================================
# QBWC Tables - QuickBooks Web Connector Integration
# ============================================================================

class QBWCSyncSession(Base):
    """QBWC sync session table - tracks active Web Connector sync sessions"""
    __tablename__ = 'qbwc_sync_sessions'

    id = Column(Integer, primary_key=True)
    ticket = Column(String(36), nullable=False, unique=True)  # UUID session ticket
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False, server_default='1')
    company_file = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, server_default='active')  # active, completed, failed
    queries_total = Column(Integer, nullable=True, server_default='0')
    queries_completed = Column(Integer, nullable=True, server_default='0')
    current_query_type = Column(String(50), nullable=True)  # 'profit_loss', 'employees'
    current_period = Column(String(7), nullable=True)  # 'YYYY-MM' format
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization")
    sync_history = relationship("QBWCSyncHistory", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_qbwc_sync_sessions_ticket', 'ticket'),
        Index('idx_qbwc_sync_sessions_status', 'status'),
        Index('idx_qbwc_sync_sessions_created_at', 'created_at'),
        Index('idx_qbwc_sync_sessions_org_id', 'organization_id'),
        CheckConstraint("status IN ('active', 'completed', 'failed')", name='chk_qbwc_session_status'),
    )


class QBWCAccountMapping(Base):
    """QBWC account mapping table - maps QuickBooks account names to QBR metric keys"""
    __tablename__ = 'qbwc_account_mappings'

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False, server_default='1')
    qbr_metric_key = Column(String(50), nullable=False)  # e.g., 'mrr', 'nrr', 'employee_expense'
    qb_account_pattern = Column(String(255), nullable=False)  # Pattern to match QB account names
    match_type = Column(String(20), nullable=False, server_default='contains')  # contains, exact, regex
    is_active = Column(Boolean, nullable=False, server_default='true')
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    organization = relationship("Organization")

    __table_args__ = (
        UniqueConstraint('organization_id', 'qbr_metric_key', 'qb_account_pattern',
                        name='uq_qbwc_mapping_org_metric_pattern'),
        Index('idx_qbwc_account_mappings_org_id', 'organization_id'),
        Index('idx_qbwc_account_mappings_metric_key', 'qbr_metric_key'),
        Index('idx_qbwc_account_mappings_is_active', 'is_active'),
        CheckConstraint("match_type IN ('contains', 'exact', 'regex')", name='chk_qbwc_mapping_match_type'),
    )


class QBWCSyncHistory(Base):
    """QBWC sync history table - stores raw sync data for debugging and audit"""
    __tablename__ = 'qbwc_sync_history'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('qbwc_sync_sessions.id', ondelete='CASCADE'), nullable=True)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False, server_default='1')
    sync_type = Column(String(50), nullable=False)  # 'profit_loss', 'employees'
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    raw_response = Column(Text, nullable=True)  # Original QBXML response
    parsed_data = Column(JSONB, nullable=True)  # Parsed account/balance data
    metrics_updated = Column(Integer, nullable=True, server_default='0')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')

    # Relationships
    session = relationship("QBWCSyncSession", back_populates="sync_history")
    organization = relationship("Organization")

    __table_args__ = (
        Index('idx_qbwc_sync_history_session_id', 'session_id'),
        Index('idx_qbwc_sync_history_org_id', 'organization_id'),
        Index('idx_qbwc_sync_history_sync_type', 'sync_type'),
        Index('idx_qbwc_sync_history_org_period', 'organization_id', 'period_start'),
        Index('idx_qbwc_sync_history_created_at', 'created_at'),
    )


class QBRAuditLog(Base):
    """QBR audit log table - tracks all access attempts to QBR data for compliance"""
    __tablename__ = 'qbr_audit_log'

    id = Column(Integer, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False, server_default='CURRENT_TIMESTAMP')
    user_email = Column(String(255), nullable=False)  # 'anonymous' if not authenticated
    action = Column(String(50), nullable=False)  # dashboard_view, metrics_request, qbwc_sync, qbwc_auth, export
    success = Column(Boolean, nullable=False, server_default='true')
    resource = Column(String(100), nullable=True)  # Specific resource accessed
    details = Column(JSONB, nullable=True)  # Additional context (period, filters, etc.)
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    failure_reason = Column(String(255), nullable=True)  # Why access was denied

    __table_args__ = (
        Index('idx_qbr_audit_log_timestamp', 'timestamp'),
        Index('idx_qbr_audit_log_user_email', 'user_email'),
        Index('idx_qbr_audit_log_action', 'action'),
        Index('idx_qbr_audit_log_success', 'success'),
        Index('idx_qbr_audit_log_timestamp_action', 'timestamp', 'action'),
    )
