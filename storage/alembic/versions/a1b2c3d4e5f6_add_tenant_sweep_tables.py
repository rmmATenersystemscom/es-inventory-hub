"""add_tenant_sweep_tables

Revision ID: a1b2c3d4e5f6
Revises: d5e6f7g8h9i0
Create Date: 2025-12-15

TenantSweep tables for storing M365 tenant security audit results.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd5e6f7g8h9i0'
branch_labels = None
depends_on = None


def upgrade():
    # Create tenant_sweep_audits table
    op.create_table(
        'tenant_sweep_audits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_name', sa.String(255), nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('started_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', TIMESTAMP(timezone=True), nullable=True),
        sa.Column('summary', JSONB(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('initiated_by', sa.String(255), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name='chk_tenant_sweep_audit_status')
    )

    # Create indexes for tenant_sweep_audits
    op.create_index('idx_tenant_sweep_audits_tenant_name', 'tenant_sweep_audits', ['tenant_name'])
    op.create_index('idx_tenant_sweep_audits_tenant_id', 'tenant_sweep_audits', ['tenant_id'])
    op.create_index('idx_tenant_sweep_audits_status', 'tenant_sweep_audits', ['status'])
    op.create_index('idx_tenant_sweep_audits_started_at', 'tenant_sweep_audits', ['started_at'])

    # Create tenant_sweep_findings table
    op.create_table(
        'tenant_sweep_findings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('audit_id', sa.Integer(), sa.ForeignKey('tenant_sweep_audits.id', ondelete='CASCADE'), nullable=False),
        sa.Column('check_id', sa.String(100), nullable=False),
        sa.Column('check_name', sa.String(255), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('current_value', sa.Text(), nullable=True),
        sa.Column('expected_value', sa.Text(), nullable=True),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('created_at', TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.CheckConstraint("severity IN ('Critical', 'High', 'Medium', 'Low', 'Info')", name='chk_tenant_sweep_finding_severity'),
        sa.CheckConstraint("status IN ('pass', 'fail', 'warning', 'error')", name='chk_tenant_sweep_finding_status')
    )

    # Create indexes for tenant_sweep_findings
    op.create_index('idx_tenant_sweep_findings_audit_id', 'tenant_sweep_findings', ['audit_id'])
    op.create_index('idx_tenant_sweep_findings_check_id', 'tenant_sweep_findings', ['check_id'])
    op.create_index('idx_tenant_sweep_findings_severity', 'tenant_sweep_findings', ['severity'])
    op.create_index('idx_tenant_sweep_findings_status', 'tenant_sweep_findings', ['status'])
    op.create_index('idx_tenant_sweep_findings_audit_severity', 'tenant_sweep_findings', ['audit_id', 'severity'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_tenant_sweep_findings_audit_severity', 'tenant_sweep_findings')
    op.drop_index('idx_tenant_sweep_findings_status', 'tenant_sweep_findings')
    op.drop_index('idx_tenant_sweep_findings_severity', 'tenant_sweep_findings')
    op.drop_index('idx_tenant_sweep_findings_check_id', 'tenant_sweep_findings')
    op.drop_index('idx_tenant_sweep_findings_audit_id', 'tenant_sweep_findings')
    op.drop_table('tenant_sweep_findings')

    op.drop_index('idx_tenant_sweep_audits_started_at', 'tenant_sweep_audits')
    op.drop_index('idx_tenant_sweep_audits_status', 'tenant_sweep_audits')
    op.drop_index('idx_tenant_sweep_audits_tenant_id', 'tenant_sweep_audits')
    op.drop_index('idx_tenant_sweep_audits_tenant_name', 'tenant_sweep_audits')
    op.drop_table('tenant_sweep_audits')
