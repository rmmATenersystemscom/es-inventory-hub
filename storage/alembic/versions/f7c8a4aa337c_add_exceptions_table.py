"""add_exceptions_table

Revision ID: f7c8a4aa337c
Revises: 0600c13a315b
Create Date: 2025-09-07 01:15:13.632475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7c8a4aa337c'
down_revision: Union[str, None] = '0600c13a315b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create exceptions table
    op.create_table('exceptions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('date_found', sa.Date(), nullable=False, server_default=sa.text('CURRENT_DATE')),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('hostname', sa.String(length=255), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_exceptions_type_date', 'exceptions', ['type', 'date_found'], unique=False)
    op.create_index('ix_exceptions_hostname', 'exceptions', ['hostname'], unique=False)
    op.create_index('ix_exceptions_resolved', 'exceptions', ['resolved'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_exceptions_resolved', table_name='exceptions')
    op.drop_index('ix_exceptions_hostname', table_name='exceptions')
    op.drop_index('ix_exceptions_type_date', table_name='exceptions')
    
    # Drop table
    op.drop_table('exceptions')
