"""Add qbr_client_metrics table for historical per-client data

Revision ID: 938e3c228146
Revises: 15e32b8bed93
Create Date: 2025-11-25 17:23:06.497484

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '938e3c228146'
down_revision: Union[str, None] = '15e32b8bed93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'qbr_client_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(7), nullable=False),
        sa.Column('client_name', sa.String(255), nullable=False),
        sa.Column('seats', sa.Integer(), server_default='0'),
        sa.Column('endpoints', sa.Integer(), server_default='0'),
        sa.Column('data_source', sa.String(20), server_default='imported'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_qbr_client_metrics_period', 'qbr_client_metrics', ['period'])
    op.create_index('idx_qbr_client_metrics_client', 'qbr_client_metrics', ['client_name'])
    op.create_index('idx_qbr_client_metrics_period_client', 'qbr_client_metrics', ['period', 'client_name'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_qbr_client_metrics_period_client', 'qbr_client_metrics')
    op.drop_index('idx_qbr_client_metrics_client', 'qbr_client_metrics')
    op.drop_index('idx_qbr_client_metrics_period', 'qbr_client_metrics')
    op.drop_table('qbr_client_metrics')
