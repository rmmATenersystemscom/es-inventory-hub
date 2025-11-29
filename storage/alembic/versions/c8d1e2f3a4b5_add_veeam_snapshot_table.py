"""add_veeam_snapshot_table

Revision ID: c8d1e2f3a4b5
Revises: 19dbffbf4e06
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision = 'c8d1e2f3a4b5'
down_revision = '19dbffbf4e06'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'veeam_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('company_uid', sa.String(255), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('storage_gb', sa.Numeric(12, 2), nullable=True),
        sa.Column('quota_gb', sa.Numeric(12, 2), nullable=True),
        sa.Column('usage_pct', sa.Numeric(5, 1), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'company_uid', name='uq_veeam_snapshot_date_company')
    )

    # Create indexes
    op.create_index('idx_veeam_snapshot_date', 'veeam_snapshot', ['snapshot_date'])
    op.create_index('idx_veeam_snapshot_company_uid', 'veeam_snapshot', ['company_uid'])
    op.create_index('idx_veeam_snapshot_org_name', 'veeam_snapshot', ['organization_name'])


def downgrade():
    op.drop_index('idx_veeam_snapshot_org_name', 'veeam_snapshot')
    op.drop_index('idx_veeam_snapshot_company_uid', 'veeam_snapshot')
    op.drop_index('idx_veeam_snapshot_date', 'veeam_snapshot')
    op.drop_table('veeam_snapshot')
