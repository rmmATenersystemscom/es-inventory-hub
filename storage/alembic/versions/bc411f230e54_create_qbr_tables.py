"""create_qbr_tables

Revision ID: bc411f230e54
Revises: 49ba3539dcb9
Create Date: 2025-11-12 21:33:21.726661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc411f230e54'
down_revision: Union[str, None] = '49ba3539dcb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organization table
    op.create_table(
        'organization',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Insert Enersystems organization
    op.execute("INSERT INTO organization (id, name) VALUES (1, 'Enersystems, LLC')")

    # Create qbr_metrics_monthly table
    op.create_table(
        'qbr_metrics_monthly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('data_source', sa.String(length=20), server_default='collected', nullable=False),
        sa.Column('collected_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('manually_entered_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendor.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('period', 'metric_name', 'organization_id', 'vendor_id', name='uq_metrics_monthly_period_metric_org_vendor')
    )
    op.create_index('idx_qbr_metrics_monthly_period', 'qbr_metrics_monthly', ['period'])
    op.create_index('idx_qbr_metrics_monthly_metric_name', 'qbr_metrics_monthly', ['metric_name'])
    op.create_index('idx_qbr_metrics_monthly_org_id', 'qbr_metrics_monthly', ['organization_id'])
    op.create_index('idx_qbr_metrics_monthly_vendor_id', 'qbr_metrics_monthly', ['vendor_id'])
    op.create_index('idx_qbr_metrics_monthly_period_metric', 'qbr_metrics_monthly', ['period', 'metric_name'])
    op.create_index('idx_qbr_metrics_monthly_data_source', 'qbr_metrics_monthly', ['data_source'])

    # Create qbr_metrics_quarterly table
    op.create_table(
        'qbr_metrics_quarterly',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('metric_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('period', 'metric_name', 'organization_id', name='uq_metrics_quarterly_period_metric_org')
    )
    op.create_index('idx_qbr_metrics_quarterly_period', 'qbr_metrics_quarterly', ['period'])
    op.create_index('idx_qbr_metrics_quarterly_metric_name', 'qbr_metrics_quarterly', ['metric_name'])
    op.create_index('idx_qbr_metrics_quarterly_org_id', 'qbr_metrics_quarterly', ['organization_id'])

    # Create qbr_smartnumbers table
    op.create_table(
        'qbr_smartnumbers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('period_type', sa.String(length=20), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('kpi_name', sa.String(length=100), nullable=False),
        sa.Column('kpi_value', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('calculation_method', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('period', 'kpi_name', 'organization_id', name='uq_smartnumbers_period_kpi_org')
    )
    op.create_index('idx_qbr_smartnumbers_period', 'qbr_smartnumbers', ['period'])
    op.create_index('idx_qbr_smartnumbers_kpi_name', 'qbr_smartnumbers', ['kpi_name'])
    op.create_index('idx_qbr_smartnumbers_org_id', 'qbr_smartnumbers', ['organization_id'])

    # Create qbr_thresholds table
    op.create_table(
        'qbr_thresholds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=100), nullable=False),
        sa.Column('threshold_type', sa.String(length=20), nullable=False),
        sa.Column('threshold_value', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('metric_name', 'threshold_type', 'organization_id', name='uq_thresholds_metric_type_org')
    )
    op.create_index('idx_qbr_thresholds_metric_name', 'qbr_thresholds', ['metric_name'])
    op.create_index('idx_qbr_thresholds_org_id', 'qbr_thresholds', ['organization_id'])

    # Create qbr_collection_log table
    op.create_table(
        'qbr_collection_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collection_started_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('collection_ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metrics_collected', sa.Integer(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendor.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_qbr_collection_log_started_at', 'qbr_collection_log', ['collection_started_at'])
    op.create_index('idx_qbr_collection_log_period', 'qbr_collection_log', ['period'])
    op.create_index('idx_qbr_collection_log_vendor_id', 'qbr_collection_log', ['vendor_id'])
    op.create_index('idx_qbr_collection_log_status', 'qbr_collection_log', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('qbr_collection_log')
    op.drop_table('qbr_thresholds')
    op.drop_table('qbr_smartnumbers')
    op.drop_table('qbr_metrics_quarterly')
    op.drop_table('qbr_metrics_monthly')
    op.drop_table('organization')
