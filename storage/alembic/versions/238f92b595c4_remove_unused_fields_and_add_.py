"""Remove unused fields and add ThreatLocker-specific fields

Revision ID: 238f92b595c4
Revises: 2773cae6a4a9
Create Date: 2025-09-12 21:58:17.324696

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '238f92b595c4'
down_revision: Union[str, None] = '2773cae6a4a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add ThreatLocker-specific fields
    op.add_column('device_snapshot', sa.Column('organization_id', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('computer_group', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('security_mode', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('deny_count_1d', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('deny_count_3d', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('deny_count_7d', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('install_date', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('is_locked_out', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('is_isolated', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('agent_version', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('has_checked_in', sa.Boolean(), nullable=True))
    
    # Add indexes for new fields
    op.create_index('idx_device_snapshot_organization_id', 'device_snapshot', ['organization_id'])
    op.create_index('idx_device_snapshot_computer_group', 'device_snapshot', ['computer_group'])
    op.create_index('idx_device_snapshot_security_mode', 'device_snapshot', ['security_mode'])
    op.create_index('idx_device_snapshot_deny_count_7d', 'device_snapshot', ['deny_count_7d'])
    op.create_index('idx_device_snapshot_install_date', 'device_snapshot', ['install_date'])
    op.create_index('idx_device_snapshot_is_locked_out', 'device_snapshot', ['is_locked_out'])
    op.create_index('idx_device_snapshot_is_isolated', 'device_snapshot', ['is_isolated'])
    
    # Remove unused fields (35 fields not used by ThreatLocker)
    op.drop_column('device_snapshot', 'serial_number')
    op.drop_column('device_snapshot', 'location_name')
    op.drop_column('device_snapshot', 'system_name')
    op.drop_column('device_snapshot', 'last_logged_in_user')
    op.drop_column('device_snapshot', 'os_release_id')
    op.drop_column('device_snapshot', 'os_build')
    op.drop_column('device_snapshot', 'os_architecture')
    op.drop_column('device_snapshot', 'os_manufacturer')
    op.drop_column('device_snapshot', 'device_timezone')
    op.drop_column('device_snapshot', 'ip_addresses')
    op.drop_column('device_snapshot', 'ipv4_addresses')
    op.drop_column('device_snapshot', 'ipv6_addresses')
    op.drop_column('device_snapshot', 'mac_addresses')
    op.drop_column('device_snapshot', 'public_ip')
    op.drop_column('device_snapshot', 'system_manufacturer')
    op.drop_column('device_snapshot', 'system_model')
    op.drop_column('device_snapshot', 'cpu_model')
    op.drop_column('device_snapshot', 'cpu_cores')
    op.drop_column('device_snapshot', 'cpu_threads')
    op.drop_column('device_snapshot', 'cpu_speed_mhz')
    op.drop_column('device_snapshot', 'memory_gib')
    op.drop_column('device_snapshot', 'memory_bytes')
    op.drop_column('device_snapshot', 'volumes')
    op.drop_column('device_snapshot', 'bios_serial')
    op.drop_column('device_snapshot', 'last_update')
    op.drop_column('device_snapshot', 'last_boot_time')
    op.drop_column('device_snapshot', 'has_tpm')
    op.drop_column('device_snapshot', 'tpm_enabled')
    op.drop_column('device_snapshot', 'tpm_version')
    op.drop_column('device_snapshot', 'secure_boot_available')
    op.drop_column('device_snapshot', 'secure_boot_enabled')
    op.drop_column('device_snapshot', 'health_state')
    op.drop_column('device_snapshot', 'antivirus_status')
    op.drop_column('device_snapshot', 'tags')
    op.drop_column('device_snapshot', 'notes')
    op.drop_column('device_snapshot', 'approval_status')
    op.drop_column('device_snapshot', 'node_class')
    op.drop_column('device_snapshot', 'system_domain')
    
    # Remove indexes for dropped columns (only the ones that exist)
    op.drop_index('idx_device_snapshot_serial_number', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_location_name', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_system_name', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_last_update', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_public_ip', table_name='device_snapshot')


def downgrade() -> None:
    # Re-add dropped columns
    op.add_column('device_snapshot', sa.Column('system_domain', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('node_class', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('approval_status', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tags', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('antivirus_status', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('health_state', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_enabled', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('secure_boot_available', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_version', sa.String(50), nullable=True))
    op.add_column('device_snapshot', sa.Column('tpm_enabled', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('has_tpm', sa.Boolean(), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_boot_time', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_update', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('device_snapshot', sa.Column('bios_serial', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('volumes', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('memory_bytes', sa.BigInteger(), nullable=True))
    op.add_column('device_snapshot', sa.Column('memory_gib', sa.BigInteger(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_speed_mhz', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_threads', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_cores', sa.Integer(), nullable=True))
    op.add_column('device_snapshot', sa.Column('cpu_model', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_model', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_manufacturer', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('public_ip', sa.String(45), nullable=True))
    op.add_column('device_snapshot', sa.Column('mac_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('ipv6_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('ipv4_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('ip_addresses', sa.Text(), nullable=True))
    op.add_column('device_snapshot', sa.Column('device_timezone', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_manufacturer', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_architecture', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_build', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('os_release_id', sa.String(100), nullable=True))
    op.add_column('device_snapshot', sa.Column('last_logged_in_user', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('location_name', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('serial_number', sa.String(255), nullable=True))
    
    # Re-add indexes for restored columns
    op.create_index('idx_device_snapshot_public_ip', 'device_snapshot', ['public_ip'])
    op.create_index('idx_device_snapshot_last_update', 'device_snapshot', ['last_update'])
    op.create_index('idx_device_snapshot_system_name', 'device_snapshot', ['system_name'])
    op.create_index('idx_device_snapshot_location_name', 'device_snapshot', ['location_name'])
    op.create_index('idx_device_snapshot_serial_number', 'device_snapshot', ['serial_number'])
    
    # Remove ThreatLocker-specific indexes
    op.drop_index('idx_device_snapshot_is_isolated', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_is_locked_out', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_install_date', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_deny_count_7d', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_security_mode', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_computer_group', table_name='device_snapshot')
    op.drop_index('idx_device_snapshot_organization_id', table_name='device_snapshot')
    
    # Remove ThreatLocker-specific fields
    op.drop_column('device_snapshot', 'has_checked_in')
    op.drop_column('device_snapshot', 'agent_version')
    op.drop_column('device_snapshot', 'is_isolated')
    op.drop_column('device_snapshot', 'is_locked_out')
    op.drop_column('device_snapshot', 'install_date')
    op.drop_column('device_snapshot', 'deny_count_7d')
    op.drop_column('device_snapshot', 'deny_count_3d')
    op.drop_column('device_snapshot', 'deny_count_1d')
    op.drop_column('device_snapshot', 'security_mode')
    op.drop_column('device_snapshot', 'computer_group')
    op.drop_column('device_snapshot', 'organization_id')
