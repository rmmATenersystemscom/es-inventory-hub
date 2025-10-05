"""add_ninja_modal_fields_for_windows_11_24h2

Revision ID: edc5f1f6e98b
Revises: b409b4d99c50
Create Date: 2025-10-03 15:33:13.994435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edc5f1f6e98b'
down_revision: Union[str, None] = 'b409b4d99c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add location_name field for NinjaRMM location mapping
    op.add_column('device_snapshot', sa.Column('location_name', sa.String(length=255), nullable=True))
    
    # Add device_type_name field for direct device type classification
    op.add_column('device_snapshot', sa.Column('device_type_name', sa.String(length=100), nullable=True))
    
    # Add billable_status_name field for direct billing status
    op.add_column('device_snapshot', sa.Column('billable_status_name', sa.String(length=100), nullable=True))
    
    # Add indexes for the new fields
    op.create_index('idx_device_snapshot_location_name', 'device_snapshot', ['location_name'], unique=False)
    op.create_index('idx_device_snapshot_device_type_name', 'device_snapshot', ['device_type_name'], unique=False)
    op.create_index('idx_device_snapshot_billable_status_name', 'device_snapshot', ['billable_status_name'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_device_snapshot_billable_status_name', 'device_snapshot')
    op.drop_index('idx_device_snapshot_device_type_name', 'device_snapshot')
    op.drop_index('idx_device_snapshot_location_name', 'device_snapshot')
    
    # Drop columns
    op.drop_column('device_snapshot', 'billable_status_name')
    op.drop_column('device_snapshot', 'device_type_name')
    op.drop_column('device_snapshot', 'location_name')
