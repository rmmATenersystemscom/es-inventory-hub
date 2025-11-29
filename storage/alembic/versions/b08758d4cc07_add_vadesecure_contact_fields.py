"""add_vadesecure_contact_fields

Revision ID: b08758d4cc07
Revises: b4c7c3217fa9
Create Date: 2025-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b08758d4cc07'
down_revision: Union[str, None] = 'b4c7c3217fa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to vadesecure_snapshot table
    op.add_column('vadesecure_snapshot', sa.Column('migrated', sa.Boolean(), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('created_date', sa.DateTime(), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('contact_name', sa.String(255), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('phone', sa.String(50), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('address', sa.String(500), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('city', sa.String(100), nullable=True))
    op.add_column('vadesecure_snapshot', sa.Column('state', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('vadesecure_snapshot', 'state')
    op.drop_column('vadesecure_snapshot', 'city')
    op.drop_column('vadesecure_snapshot', 'address')
    op.drop_column('vadesecure_snapshot', 'phone')
    op.drop_column('vadesecure_snapshot', 'contact_name')
    op.drop_column('vadesecure_snapshot', 'created_date')
    op.drop_column('vadesecure_snapshot', 'migrated')
