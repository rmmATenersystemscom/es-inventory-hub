"""add_m365_snapshot_table

Revision ID: 6297e5d6035e
Revises: 4e078b470528
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision = '6297e5d6035e'
down_revision = '4e078b470528'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'm365_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('user_count', sa.Integer(), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'tenant_id', name='uq_m365_snapshot_date_tenant')
    )

    # Create indexes
    op.create_index('idx_m365_snapshot_date', 'm365_snapshot', ['snapshot_date'])
    op.create_index('idx_m365_snapshot_tenant_id', 'm365_snapshot', ['tenant_id'])
    op.create_index('idx_m365_snapshot_org_name', 'm365_snapshot', ['organization_name'])


def downgrade():
    op.drop_index('idx_m365_snapshot_org_name', 'm365_snapshot')
    op.drop_index('idx_m365_snapshot_tenant_id', 'm365_snapshot')
    op.drop_index('idx_m365_snapshot_date', 'm365_snapshot')
    op.drop_table('m365_snapshot')
