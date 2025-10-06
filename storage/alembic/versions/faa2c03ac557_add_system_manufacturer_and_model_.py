"""Add system manufacturer and model fields to device_snapshot

Revision ID: faa2c03ac557
Revises: edc5f1f6e98b
Create Date: 2025-10-05 20:45:51.158270

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faa2c03ac557'
down_revision: Union[str, None] = 'edc5f1f6e98b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add system manufacturer and model fields to device_snapshot table
    op.add_column('device_snapshot', sa.Column('system_manufacturer', sa.String(255), nullable=True))
    op.add_column('device_snapshot', sa.Column('system_model', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove system manufacturer and model fields from device_snapshot table
    op.drop_column('device_snapshot', 'system_model')
    op.drop_column('device_snapshot', 'system_manufacturer')
