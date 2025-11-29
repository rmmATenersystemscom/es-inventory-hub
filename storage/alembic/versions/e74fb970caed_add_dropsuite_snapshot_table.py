"""add_dropsuite_snapshot_table

Revision ID: e74fb970caed
Revises: b08758d4cc07
Create Date: 2025-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'e74fb970caed'
down_revision: Union[str, None] = 'b08758d4cc07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create dropsuite_snapshot table
    op.create_table(
        'dropsuite_snapshot',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=True),
        sa.Column('seats_used', sa.Integer(), nullable=True),
        sa.Column('archive_type', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('total_emails', sa.Integer(), nullable=True),
        sa.Column('storage_gb', sa.Numeric(10, 2), nullable=True),
        sa.Column('last_backup', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('compliance', sa.Boolean(), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('snapshot_date', 'user_id',
                           name='uq_dropsuite_snapshot_date_user')
    )

    # Create indexes
    op.create_index('idx_dropsuite_snapshot_date', 'dropsuite_snapshot', ['snapshot_date'])
    op.create_index('idx_dropsuite_snapshot_user_id', 'dropsuite_snapshot', ['user_id'])
    op.create_index('idx_dropsuite_snapshot_org_name', 'dropsuite_snapshot', ['organization_name'])
    op.create_index('idx_dropsuite_snapshot_status', 'dropsuite_snapshot', ['status'])

    # Insert Dropsuite vendor record
    op.execute("INSERT INTO vendor (name) VALUES ('Dropsuite') ON CONFLICT (name) DO NOTHING")


def downgrade() -> None:
    op.drop_index('idx_dropsuite_snapshot_status', table_name='dropsuite_snapshot')
    op.drop_index('idx_dropsuite_snapshot_org_name', table_name='dropsuite_snapshot')
    op.drop_index('idx_dropsuite_snapshot_user_id', table_name='dropsuite_snapshot')
    op.drop_index('idx_dropsuite_snapshot_date', table_name='dropsuite_snapshot')
    op.drop_table('dropsuite_snapshot')
    op.execute("DELETE FROM vendor WHERE name = 'Dropsuite'")
