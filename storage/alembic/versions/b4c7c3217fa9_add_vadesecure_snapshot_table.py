"""add_vadesecure_snapshot_table

Revision ID: b4c7c3217fa9
Revises: 938e3c228146
Create Date: 2025-11-25 18:15:24.412748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP


# revision identifiers, used by Alembic.
revision: str = 'b4c7c3217fa9'
down_revision: Union[str, None] = '938e3c228146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create vadesecure_snapshot table
    op.create_table(
        'vadesecure_snapshot',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('customer_id', sa.String(255), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('company_domain', sa.String(255), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        # License info
        sa.Column('license_id', sa.String(255), nullable=True),
        sa.Column('product_type', sa.String(100), nullable=True),
        sa.Column('license_status', sa.String(50), nullable=True),
        sa.Column('license_start_date', sa.Date(), nullable=True),
        sa.Column('license_end_date', sa.Date(), nullable=True),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        # Usage metrics
        sa.Column('usage_count', sa.Integer(), nullable=True),
        # Metadata
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('snapshot_date', 'customer_id', name='uq_vadesecure_snapshot_date_customer')
    )

    # Create indexes
    op.create_index('idx_vadesecure_snapshot_date', 'vadesecure_snapshot', ['snapshot_date'])
    op.create_index('idx_vadesecure_snapshot_customer_id', 'vadesecure_snapshot', ['customer_id'])
    op.create_index('idx_vadesecure_snapshot_customer_name', 'vadesecure_snapshot', ['customer_name'])
    op.create_index('idx_vadesecure_snapshot_license_status', 'vadesecure_snapshot', ['license_status'])

    # Add VadeSecure vendor record
    op.execute("INSERT INTO vendor (name) VALUES ('VadeSecure') ON CONFLICT (name) DO NOTHING")


def downgrade() -> None:
    # Remove VadeSecure vendor record
    op.execute("DELETE FROM vendor WHERE name = 'VadeSecure'")

    # Drop indexes
    op.drop_index('idx_vadesecure_snapshot_license_status', table_name='vadesecure_snapshot')
    op.drop_index('idx_vadesecure_snapshot_customer_name', table_name='vadesecure_snapshot')
    op.drop_index('idx_vadesecure_snapshot_customer_id', table_name='vadesecure_snapshot')
    op.drop_index('idx_vadesecure_snapshot_date', table_name='vadesecure_snapshot')

    # Drop table
    op.drop_table('vadesecure_snapshot')
