"""add_m365_user_snapshot_table

Revision ID: 19dbffbf4e06
Revises: 6297e5d6035e
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision = '19dbffbf4e06'
down_revision = '6297e5d6035e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'm365_user_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('licenses', sa.Text(), nullable=True),  # Comma-separated license names
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'tenant_id', 'username', name='uq_m365_user_snapshot_date_tenant_user')
    )

    # Create indexes
    op.create_index('idx_m365_user_snapshot_date', 'm365_user_snapshot', ['snapshot_date'])
    op.create_index('idx_m365_user_snapshot_tenant_id', 'm365_user_snapshot', ['tenant_id'])
    op.create_index('idx_m365_user_snapshot_org_name', 'm365_user_snapshot', ['organization_name'])
    op.create_index('idx_m365_user_snapshot_username', 'm365_user_snapshot', ['username'])


def downgrade():
    op.drop_index('idx_m365_user_snapshot_username', 'm365_user_snapshot')
    op.drop_index('idx_m365_user_snapshot_org_name', 'm365_user_snapshot')
    op.drop_index('idx_m365_user_snapshot_tenant_id', 'm365_user_snapshot')
    op.drop_index('idx_m365_user_snapshot_date', 'm365_user_snapshot')
    op.drop_table('m365_user_snapshot')
