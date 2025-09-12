"""update_device_snapshot_for_ninja_modal_fields

Revision ID: ceb4bd0ca93e
Revises: f7c8a4aa337c
Create Date: 2025-09-12 02:48:56.777371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ceb4bd0ca93e'
down_revision: Union[str, None] = 'f7c8a4aa337c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove fields that are not in the Ninja modal
    op.drop_column('device_snapshot', 'tpm_status')
    op.drop_column('device_snapshot', 'raw')
    op.drop_column('device_snapshot', 'attrs')
    op.drop_column('device_snapshot', 'content_hash')
    
    # Drop the index for content_hash since we're removing the column (if it exists)
    try:
        op.drop_index('idx_device_snapshot_content_hash', table_name='device_snapshot')
    except Exception:
        # Index doesn't exist, continue
        pass
    
    # Add new fields to mirror the Ninja dashboard modal (42 total fields)
    
    # Core Device Information
    op.add_column('device_snapshot', sa.Column('organization_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('location_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('display_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('device_status', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_logged_in_user', sa.String(255), nullable=True))
    
    # OS Information
    op.add_column('device_snapshot', sa.Column('os_release_id', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_build', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_architecture', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_manufacturer', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('device_timezone', sa.String(100), nullable=True))
    
    # Network Information
    op.add_column('device_snapshot', sa.Column('ip_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('ipv4_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('ipv6_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('mac_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('public_ip', sa.String(45), nullable=True))
    
    # Hardware Information
    op.add_column('device_snapshot', sa.Column('system_manufacturer', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_model', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_model', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_cores', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_threads', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_speed_mhz', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('memory_gib', sa.Numeric(10, 2), nullable=True))
    op.add_column('device_snapshot', sa.Column('memory_bytes', sa.BigInteger(), nullable=True))
    op.add_column('device_snapshot', sa.Column('volumes', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('bios_serial', sa.String(255), nullable=True))
    
    # Timestamps
    op.add_column('device_snapshot', sa.Column('last_online', sa.DateTime(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_update', sa.DateTime(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_boot_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('agent_install_timestamp', sa.DateTime(timezone=True), nullable=True))
    
    # Security Information
    op.add_column('device_snapshot', sa.Column('has_tpm', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_enabled', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_version', sa.String(50), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_available', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_enabled', sa.Boolean(), nullable=True))
    
    # Monitoring and Health
    op.add_column('device_snapshot', sa.Column('health_state', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('antivirus_status', sa.Text(), nullable=True))
    
    # Metadata
    op.add_column('device_snapshot', sa.Column('tags', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('approval_status', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('node_class', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_domain', sa.String(255), nullable=True))
    
    # Create indexes for commonly queried fields
    op.create_index('idx_device_snapshot_organization_name', 'device_snapshot', ['organization_name'])
    op.create_index('idx_device_snapshot_location_name', 'device_snapshot', ['location_name'])
    op.create_index('idx_device_snapshot_system_name', 'device_snapshot', ['system_name'])
    op.create_index('idx_device_snapshot_display_name', 'device_snapshot', ['display_name'])
    op.create_index('idx_device_snapshot_device_status', 'device_snapshot', ['device_status'])
    op.create_index('idx_device_snapshot_last_online', 'device_snapshot', ['last_online'])
    op.create_index('idx_device_snapshot_last_update', 'device_snapshot', ['last_update'])
    op.create_index('idx_device_snapshot_public_ip', 'device_snapshot', ['public_ip'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_device_snapshot_public_ip', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_last_update', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_last_online', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_device_status', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_display_name', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_system_name', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_location_name', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_organization_name', table_name='device_snapshot')
    
    # Remove all the new columns
    op.drop_column('device_snapshot', 'system_domain')
    op.drop_column('device_snapshot', 'node_class')
    op.drop_column('device_snapshot', 'approval_status')
    op.drop_column('device_snapshot', 'notes')
    op.drop_column('device_snapshot', 'tags')
    op.drop_column('device_snapshot', 'antivirus_status')
    op.drop_column('device_snapshot', 'health_state')
    op.drop_column('device_snapshot', 'secure_boot_enabled')
    op.drop_column('device_snapshot', 'secure_boot_available')
    op.drop_column('device_snapshot', 'tpm_version')
    op.drop_column('device_snapshot', 'tpm_enabled')
    op.drop_column('device_snapshot', 'has_tpm')
    op.drop_column('device_snapshot', 'agent_install_timestamp')
    op.drop_column('device_snapshot', 'last_boot_time')
    op.drop_column('device_snapshot', 'last_update')
    op.drop_column('device_snapshot', 'last_online')
    op.drop_column('device_snapshot', 'bios_serial')
    op.drop_column('device_snapshot', 'volumes')
    op.drop_column('device_snapshot', 'memory_bytes')
    op.drop_column('device_snapshot', 'memory_gib')
    op.drop_column('device_snapshot', 'cpu_speed_mhz')
    op.drop_column('device_snapshot', 'cpu_threads')
    op.drop_column('device_snapshot', 'cpu_cores')
    op.drop_column('device_snapshot', 'cpu_model')
    op.drop_column('device_snapshot', 'system_model')
    op.drop_column('device_snapshot', 'system_manufacturer')
    op.drop_column('device_snapshot', 'public_ip')
    op.drop_column('device_snapshot', 'mac_addresses')
    op.drop_column('device_snapshot', 'ipv6_addresses')
    op.drop_column('device_snapshot', 'ipv4_addresses')
    op.drop_column('device_snapshot', 'ip_addresses')
    op.drop_column('device_snapshot', 'device_timezone')
    op.drop_column('device_snapshot', 'os_manufacturer')
    op.drop_column('device_snapshot', 'os_architecture')
    op.drop_column('device_snapshot', 'os_build')
    op.drop_column('device_snapshot', 'os_release_id')
    op.drop_column('device_snapshot', 'last_logged_in_user')
    op.drop_column('device_snapshot', 'device_status')
    op.drop_column('device_snapshot', 'display_name')
    op.drop_column('device_snapshot', 'system_name')
    op.drop_column('device_snapshot', 'location_name')
    op.drop_column('device_snapshot', 'organization_name')
    
    # Restore the original fields
    op.add_column('device_snapshot', sa.Column('tpm_status', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('raw', sa.JSON(), nullable=True))
    op.add_column('device_snapshot', sa.Column('attrs', sa.JSON(), nullable=True))
    op.add_column('device_snapshot', sa.Column('content_hash', sa.String(64), nullable=True))
    
    # Restore the content_hash index
    try:
        op.create_index('idx_device_snapshot_content_hash', 'device_snapshot', ['content_hash'])
    except Exception:
        # Index might already exist, continue
        pass
