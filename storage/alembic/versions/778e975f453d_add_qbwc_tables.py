"""add_qbwc_tables

Revision ID: 778e975f453d
Revises: a1b2c3d4e5f6
Create Date: 2025-12-16 21:03:34.766558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '778e975f453d'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create qbr_audit_log table
    op.create_table('qbr_audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('timestamp', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('user_email', sa.String(length=255), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('success', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('resource', sa.String(length=100), nullable=True),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('failure_reason', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_qbr_audit_log_action', 'qbr_audit_log', ['action'], unique=False)
    op.create_index('idx_qbr_audit_log_success', 'qbr_audit_log', ['success'], unique=False)
    op.create_index('idx_qbr_audit_log_timestamp', 'qbr_audit_log', ['timestamp'], unique=False)
    op.create_index('idx_qbr_audit_log_timestamp_action', 'qbr_audit_log', ['timestamp', 'action'], unique=False)
    op.create_index('idx_qbr_audit_log_user_email', 'qbr_audit_log', ['user_email'], unique=False)

    # Create qbwc_account_mappings table
    op.create_table('qbwc_account_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('qbr_metric_key', sa.String(length=50), nullable=False),
    sa.Column('qb_account_pattern', sa.String(length=255), nullable=False),
    sa.Column('match_type', sa.String(length=20), server_default=sa.text("'contains'"), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.CheckConstraint("match_type IN ('contains', 'exact', 'regex')", name='chk_qbwc_mapping_match_type'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'qbr_metric_key', 'qb_account_pattern', name='uq_qbwc_mapping_org_metric_pattern')
    )
    op.create_index('idx_qbwc_account_mappings_is_active', 'qbwc_account_mappings', ['is_active'], unique=False)
    op.create_index('idx_qbwc_account_mappings_metric_key', 'qbwc_account_mappings', ['qbr_metric_key'], unique=False)
    op.create_index('idx_qbwc_account_mappings_org_id', 'qbwc_account_mappings', ['organization_id'], unique=False)

    # Insert default account mappings
    op.execute("""
        INSERT INTO qbwc_account_mappings (qbr_metric_key, qb_account_pattern, match_type, notes) VALUES
        ('nrr', '%Non-Recurring%', 'contains', 'Non-Recurring Revenue'),
        ('nrr', '%NRR%', 'contains', 'NRR labeled accounts'),
        ('nrr', '%Professional Services%', 'contains', 'Professional services income'),
        ('mrr', '%Monthly Recurring%', 'contains', 'Monthly Recurring Revenue'),
        ('mrr', '%MRR%', 'contains', 'MRR labeled accounts'),
        ('mrr', '%Managed Services%', 'contains', 'Managed services income'),
        ('orr', '%Other Recurring%', 'contains', 'Other Recurring Revenue'),
        ('orr', '%Annual%', 'contains', 'Annual revenue'),
        ('product_sales', '%Product Sales%', 'contains', 'Product sales'),
        ('product_sales', '%Hardware Sales%', 'contains', 'Hardware sales'),
        ('misc_revenue', '%Other Income%', 'contains', 'Miscellaneous revenue'),
        ('employee_expense', '%Payroll%', 'contains', 'Payroll expenses'),
        ('employee_expense', '%Wages%', 'contains', 'Wage expenses'),
        ('employee_expense', '%Salaries%', 'contains', 'Salary expenses'),
        ('owner_comp_taxes', '%Tax Distribution%', 'contains', 'Owner tax distributions'),
        ('owner_comp_taxes', '%Estimated Tax%', 'contains', 'Quarterly estimated taxes'),
        ('owner_comp', '%Owner Draw%', 'contains', 'Owner draws'),
        ('owner_comp', '%Owner Comp%', 'contains', 'Owner compensation'),
        ('owner_comp', '%Officer%', 'contains', 'Officer compensation'),
        ('product_cogs', '%Cost of Goods%', 'contains', 'COGS'),
        ('product_cogs', '%COGS%', 'contains', 'COGS'),
        ('other_expenses', '%Expense%', 'contains', 'General expenses (catch-all)')
    """)

    # Create qbwc_sync_sessions table
    op.create_table('qbwc_sync_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket', sa.String(length=36), nullable=False),
    sa.Column('organization_id', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('company_file', sa.String(length=500), nullable=True),
    sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
    sa.Column('queries_total', sa.Integer(), server_default=sa.text('0'), nullable=True),
    sa.Column('queries_completed', sa.Integer(), server_default=sa.text('0'), nullable=True),
    sa.Column('current_query_type', sa.String(length=50), nullable=True),
    sa.Column('current_period', sa.String(length=7), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('completed_at', postgresql.TIMESTAMP(timezone=True), nullable=True),
    sa.CheckConstraint("status IN ('active', 'completed', 'failed')", name='chk_qbwc_session_status'),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('ticket')
    )
    op.create_index('idx_qbwc_sync_sessions_created_at', 'qbwc_sync_sessions', ['created_at'], unique=False)
    op.create_index('idx_qbwc_sync_sessions_org_id', 'qbwc_sync_sessions', ['organization_id'], unique=False)
    op.create_index('idx_qbwc_sync_sessions_status', 'qbwc_sync_sessions', ['status'], unique=False)
    op.create_index('idx_qbwc_sync_sessions_ticket', 'qbwc_sync_sessions', ['ticket'], unique=False)

    # Create qbwc_sync_history table
    op.create_table('qbwc_sync_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=True),
    sa.Column('organization_id', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('sync_type', sa.String(length=50), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=False),
    sa.Column('raw_response', sa.Text(), nullable=True),
    sa.Column('parsed_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('metrics_updated', sa.Integer(), server_default=sa.text('0'), nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organization.id'], ),
    sa.ForeignKeyConstraint(['session_id'], ['qbwc_sync_sessions.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_qbwc_sync_history_created_at', 'qbwc_sync_history', ['created_at'], unique=False)
    op.create_index('idx_qbwc_sync_history_org_id', 'qbwc_sync_history', ['organization_id'], unique=False)
    op.create_index('idx_qbwc_sync_history_org_period', 'qbwc_sync_history', ['organization_id', 'period_start'], unique=False)
    op.create_index('idx_qbwc_sync_history_session_id', 'qbwc_sync_history', ['session_id'], unique=False)
    op.create_index('idx_qbwc_sync_history_sync_type', 'qbwc_sync_history', ['sync_type'], unique=False)


def downgrade() -> None:
    # Drop qbwc_sync_history
    op.drop_index('idx_qbwc_sync_history_sync_type', table_name='qbwc_sync_history')
    op.drop_index('idx_qbwc_sync_history_session_id', table_name='qbwc_sync_history')
    op.drop_index('idx_qbwc_sync_history_org_period', table_name='qbwc_sync_history')
    op.drop_index('idx_qbwc_sync_history_org_id', table_name='qbwc_sync_history')
    op.drop_index('idx_qbwc_sync_history_created_at', table_name='qbwc_sync_history')
    op.drop_table('qbwc_sync_history')

    # Drop qbwc_sync_sessions
    op.drop_index('idx_qbwc_sync_sessions_ticket', table_name='qbwc_sync_sessions')
    op.drop_index('idx_qbwc_sync_sessions_status', table_name='qbwc_sync_sessions')
    op.drop_index('idx_qbwc_sync_sessions_org_id', table_name='qbwc_sync_sessions')
    op.drop_index('idx_qbwc_sync_sessions_created_at', table_name='qbwc_sync_sessions')
    op.drop_table('qbwc_sync_sessions')

    # Drop qbwc_account_mappings
    op.drop_index('idx_qbwc_account_mappings_org_id', table_name='qbwc_account_mappings')
    op.drop_index('idx_qbwc_account_mappings_metric_key', table_name='qbwc_account_mappings')
    op.drop_index('idx_qbwc_account_mappings_is_active', table_name='qbwc_account_mappings')
    op.drop_table('qbwc_account_mappings')

    # Drop qbr_audit_log
    op.drop_index('idx_qbr_audit_log_user_email', table_name='qbr_audit_log')
    op.drop_index('idx_qbr_audit_log_timestamp_action', table_name='qbr_audit_log')
    op.drop_index('idx_qbr_audit_log_timestamp', table_name='qbr_audit_log')
    op.drop_index('idx_qbr_audit_log_success', table_name='qbr_audit_log')
    op.drop_index('idx_qbr_audit_log_action', table_name='qbr_audit_log')
    op.drop_table('qbr_audit_log')
