"""update_qbr_thresholds_schema_denormalized

Revision ID: 15e32b8bed93
Revises: c4b9ed4fad9d
Create Date: 2025-11-15 06:47:14.787825

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15e32b8bed93'
down_revision: Union[str, None] = 'c4b9ed4fad9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old unique constraint
    op.drop_constraint('uq_thresholds_metric_type_org', 'qbr_thresholds', type_='unique')

    # Drop old columns
    op.drop_column('qbr_thresholds', 'threshold_type')
    op.drop_column('qbr_thresholds', 'threshold_value')

    # Add new denormalized columns
    op.add_column('qbr_thresholds',
                  sa.Column('green_min', sa.Numeric(12, 4), nullable=True))
    op.add_column('qbr_thresholds',
                  sa.Column('green_max', sa.Numeric(12, 4), nullable=True))
    op.add_column('qbr_thresholds',
                  sa.Column('yellow_min', sa.Numeric(12, 4), nullable=True))
    op.add_column('qbr_thresholds',
                  sa.Column('yellow_max', sa.Numeric(12, 4), nullable=True))
    op.add_column('qbr_thresholds',
                  sa.Column('red_threshold', sa.Numeric(12, 4), nullable=True))
    op.add_column('qbr_thresholds',
                  sa.Column('notes', sa.String(500), nullable=True))

    # Create new unique constraint (one threshold config per metric per org)
    op.create_unique_constraint(
        'uq_thresholds_metric_org',
        'qbr_thresholds',
        ['metric_name', 'organization_id']
    )


def downgrade() -> None:
    # Drop new unique constraint
    op.drop_constraint('uq_thresholds_metric_org', 'qbr_thresholds', type_='unique')

    # Drop new columns
    op.drop_column('qbr_thresholds', 'notes')
    op.drop_column('qbr_thresholds', 'red_threshold')
    op.drop_column('qbr_thresholds', 'yellow_max')
    op.drop_column('qbr_thresholds', 'yellow_min')
    op.drop_column('qbr_thresholds', 'green_max')
    op.drop_column('qbr_thresholds', 'green_min')

    # Add back old columns
    op.add_column('qbr_thresholds',
                  sa.Column('threshold_type', sa.String(20), nullable=False))
    op.add_column('qbr_thresholds',
                  sa.Column('threshold_value', sa.Numeric(12, 2), nullable=True))

    # Recreate old unique constraint
    op.create_unique_constraint(
        'uq_thresholds_metric_type_org',
        'qbr_thresholds',
        ['metric_name', 'threshold_type', 'organization_id']
    )
