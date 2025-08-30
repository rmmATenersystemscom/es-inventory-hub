"""Initial migration

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sites table
    op.create_table('sites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('ninja_site_id', sa.String(length=100), nullable=True),
        sa.Column('threatlocker_tenant_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create devices table
    op.create_table('devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('ninja_device_id', sa.String(length=100), nullable=True),
        sa.Column('threatlocker_device_id', sa.String(length=100), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('node_class', sa.String(length=100), nullable=True),
        sa.Column('is_spare', sa.Boolean(), nullable=True),
        sa.Column('is_server', sa.Boolean(), nullable=True),
        sa.Column('is_billable', sa.Boolean(), nullable=True),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ninja_device_id'),
        sa.UniqueConstraint('threatlocker_device_id')
    )
    
    # Create device_snapshots table
    op.create_table('device_snapshots',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('data_hash', sa.String(length=64), nullable=False),
        sa.Column('source_system', sa.String(length=50), nullable=False),
        sa.Column('ninja_data', sa.Text(), nullable=True),
        sa.Column('threatlocker_data', sa.Text(), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('node_class', sa.String(length=100), nullable=True),
        sa.Column('os_name', sa.String(length=255), nullable=True),
        sa.Column('os_version', sa.String(length=255), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('is_spare', sa.Boolean(), nullable=True),
        sa.Column('is_server', sa.Boolean(), nullable=True),
        sa.Column('is_billable', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'snapshot_date', 'source_system', name='uq_device_date_source')
    )
    
    # Create daily_counts table
    op.create_table('daily_counts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('count_date', sa.DateTime(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('total_devices', sa.Integer(), nullable=True),
        sa.Column('servers', sa.Integer(), nullable=True),
        sa.Column('workstations', sa.Integer(), nullable=True),
        sa.Column('spare_devices', sa.Integer(), nullable=True),
        sa.Column('billable_devices', sa.Integer(), nullable=True),
        sa.Column('ninja_devices', sa.Integer(), nullable=True),
        sa.Column('threatlocker_devices', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('count_date', 'site_id', name='uq_daily_count_date_site')
    )
    
    # Create month_end_counts table
    op.create_table('month_end_counts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('month_end_date', sa.DateTime(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('total_devices', sa.Integer(), nullable=True),
        sa.Column('servers', sa.Integer(), nullable=True),
        sa.Column('workstations', sa.Integer(), nullable=True),
        sa.Column('spare_devices', sa.Integer(), nullable=True),
        sa.Column('billable_devices', sa.Integer(), nullable=True),
        sa.Column('ninja_devices', sa.Integer(), nullable=True),
        sa.Column('threatlocker_devices', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('month_end_date', 'site_id', name='uq_month_end_date_site')
    )
    
    # Create indexes
    op.create_index('idx_device_ninja_id', 'devices', ['ninja_device_id'], unique=False)
    op.create_index('idx_device_threatlocker_id', 'devices', ['threatlocker_device_id'], unique=False)
    op.create_index('idx_device_site', 'devices', ['site_id'], unique=False)
    op.create_index('idx_device_spare', 'devices', ['is_spare'], unique=False)
    op.create_index('idx_device_server', 'devices', ['is_server'], unique=False)
    op.create_index('idx_device_billable', 'devices', ['is_billable'], unique=False)
    op.create_index('idx_snapshot_device_date', 'device_snapshots', ['device_id', 'snapshot_date'], unique=False)
    op.create_index('idx_snapshot_date', 'device_snapshots', ['snapshot_date'], unique=False)
    op.create_index('idx_snapshot_hash', 'device_snapshots', ['data_hash'], unique=False)
    op.create_index('idx_snapshot_source', 'device_snapshots', ['source_system'], unique=False)
    op.create_index('idx_daily_counts_date', 'daily_counts', ['count_date'], unique=False)
    op.create_index('idx_daily_counts_site', 'daily_counts', ['site_id'], unique=False)
    op.create_index('idx_month_end_date', 'month_end_counts', ['month_end_date'], unique=False)
    op.create_index('idx_month_end_site', 'month_end_counts', ['site_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_month_end_site', table_name='month_end_counts')
    op.drop_index('idx_month_end_date', table_name='month_end_counts')
    op.drop_index('idx_daily_counts_site', table_name='daily_counts')
    op.drop_index('idx_daily_counts_date', table_name='daily_counts')
    op.drop_index('idx_snapshot_source', table_name='device_snapshots')
    op.drop_index('idx_snapshot_hash', table_name='device_snapshots')
    op.drop_index('idx_snapshot_date', table_name='device_snapshots')
    op.drop_index('idx_snapshot_device_date', table_name='device_snapshots')
    op.drop_index('idx_device_billable', table_name='devices')
    op.drop_index('idx_device_server', table_name='devices')
    op.drop_index('idx_device_spare', table_name='devices')
    op.drop_index('idx_device_site', table_name='devices')
    op.drop_index('idx_device_threatlocker_id', table_name='devices')
    op.drop_index('idx_device_ninja_id', table_name='devices')
    
    # Drop tables
    op.drop_table('month_end_counts')
    op.drop_table('daily_counts')
    op.drop_table('device_snapshots')
    op.drop_table('devices')
    op.drop_table('sites')
