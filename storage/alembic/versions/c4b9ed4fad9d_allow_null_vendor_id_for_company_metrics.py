"""allow_null_vendor_id_for_company_metrics

Revision ID: c4b9ed4fad9d
Revises: bc411f230e54
Create Date: 2025-11-15 01:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4b9ed4fad9d'
down_revision = 'bc411f230e54'
branch_labels = None
depends_on = None


def upgrade():
    # Allow NULL vendor_id for company-wide metrics (employees, revenue, etc.)
    op.alter_column('qbr_metrics_monthly', 'vendor_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)

    # Drop the unique constraint that includes vendor_id
    op.drop_constraint('uq_metrics_monthly_period_metric_org_vendor', 'qbr_metrics_monthly', type_='unique')

    # Recreate unique constraint with partial index (vendor_id NOT NULL)
    # This allows multiple NULL vendor_ids while still maintaining uniqueness for non-NULL values
    op.create_index(
        'idx_qbr_metrics_monthly_unique_with_vendor',
        'qbr_metrics_monthly',
        ['period', 'metric_name', 'organization_id', 'vendor_id'],
        unique=True,
        postgresql_where=sa.text('vendor_id IS NOT NULL')
    )

    # Add unique constraint for NULL vendor_id entries
    op.create_index(
        'idx_qbr_metrics_monthly_unique_without_vendor',
        'qbr_metrics_monthly',
        ['period', 'metric_name', 'organization_id'],
        unique=True,
        postgresql_where=sa.text('vendor_id IS NULL')
    )


def downgrade():
    # Drop the partial indexes
    op.drop_index('idx_qbr_metrics_monthly_unique_without_vendor', table_name='qbr_metrics_monthly')
    op.drop_index('idx_qbr_metrics_monthly_unique_with_vendor', table_name='qbr_metrics_monthly')

    # Recreate the original unique constraint
    op.create_unique_constraint(
        'uq_metrics_monthly_period_metric_org_vendor',
        'qbr_metrics_monthly',
        ['period', 'metric_name', 'organization_id', 'vendor_id']
    )

    # Make vendor_id NOT NULL again
    op.alter_column('qbr_metrics_monthly', 'vendor_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
