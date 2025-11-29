"""add_duo_user_snapshot_table

Revision ID: d5e6f7g8h9i0
Revises: c8d1e2f3a4b5
Create Date: 2025-11-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision = 'd5e6f7g8h9i0'
down_revision = 'c8d1e2f3a4b5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'duo_user_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('account_id', sa.String(255), nullable=False),  # Duo account ID
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=False),  # Duo user ID
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),  # active, bypass, disabled, locked out
        sa.Column('last_login', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),  # Primary phone number
        sa.Column('is_enrolled', sa.Boolean(), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'account_id', 'user_id', name='uq_duo_user_snapshot_date_account_user')
    )

    # Create indexes
    op.create_index('idx_duo_user_snapshot_date', 'duo_user_snapshot', ['snapshot_date'])
    op.create_index('idx_duo_user_snapshot_account_id', 'duo_user_snapshot', ['account_id'])
    op.create_index('idx_duo_user_snapshot_user_id', 'duo_user_snapshot', ['user_id'])
    op.create_index('idx_duo_user_snapshot_org_name', 'duo_user_snapshot', ['organization_name'])


def downgrade():
    op.drop_index('idx_duo_user_snapshot_org_name', 'duo_user_snapshot')
    op.drop_index('idx_duo_user_snapshot_user_id', 'duo_user_snapshot')
    op.drop_index('idx_duo_user_snapshot_account_id', 'duo_user_snapshot')
    op.drop_index('idx_duo_user_snapshot_date', 'duo_user_snapshot')
    op.drop_table('duo_user_snapshot')
