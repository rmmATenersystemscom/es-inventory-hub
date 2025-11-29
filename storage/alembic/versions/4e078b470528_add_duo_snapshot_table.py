"""add_duo_snapshot_table

Revision ID: 4e078b470528
Revises: e74fb970caed
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP


# revision identifiers, used by Alembic.
revision = '4e078b470528'
down_revision = 'e74fb970caed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'duo_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('account_id', sa.String(255), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('user_count', sa.Integer(), nullable=True),
        sa.Column('admin_count', sa.Integer(), nullable=True),
        sa.Column('integration_count', sa.Integer(), nullable=True),
        sa.Column('phone_count', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('last_activity', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('group_count', sa.Integer(), nullable=True),
        sa.Column('webauthn_count', sa.Integer(), nullable=True),
        sa.Column('last_login', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('enrollment_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('auth_methods', JSONB(), nullable=True),
        sa.Column('directory_sync', sa.Boolean(), nullable=True),
        sa.Column('telephony_credits', sa.Integer(), nullable=True),
        sa.Column('auth_volume', sa.Integer(), nullable=True),
        sa.Column('failed_auth_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('peak_usage', sa.String(50), nullable=True),
        sa.Column('account_type', sa.String(100), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'account_id', name='uq_duo_snapshot_date_account')
    )

    # Create indexes
    op.create_index('idx_duo_snapshot_date', 'duo_snapshot', ['snapshot_date'])
    op.create_index('idx_duo_snapshot_account_id', 'duo_snapshot', ['account_id'])
    op.create_index('idx_duo_snapshot_org_name', 'duo_snapshot', ['organization_name'])
    op.create_index('idx_duo_snapshot_status', 'duo_snapshot', ['status'])


def downgrade():
    op.drop_index('idx_duo_snapshot_status', 'duo_snapshot')
    op.drop_index('idx_duo_snapshot_org_name', 'duo_snapshot')
    op.drop_index('idx_duo_snapshot_account_id', 'duo_snapshot')
    op.drop_index('idx_duo_snapshot_date', 'duo_snapshot')
    op.drop_table('duo_snapshot')
