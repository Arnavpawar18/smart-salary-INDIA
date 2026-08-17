"""Add payroll core tables: payroll_periods, payroll_runs, payroll_run_items

Revision ID: 004_add_payroll_core
Revises: 003_add_enterprise_organizations
Create Date: 2026-08-17 18:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '004_add_payroll_core'
down_revision: str | None = '003_add_enterprise_organizations'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create payroll_periods
    op.create_table(
        'payroll_periods',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('financial_year', sa.String(length=20), nullable=False),
        sa.Column('period_code', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='OPEN', nullable=False),
        sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'period_code', name='uq_payroll_period_org_code')
    )
    op.create_index(op.f('ix_payroll_periods_financial_year'), 'payroll_periods', ['financial_year'], unique=False)
    op.create_index(op.f('ix_payroll_periods_organization_id'), 'payroll_periods', ['organization_id'], unique=False)
    op.create_index(op.f('ix_payroll_periods_period_code'), 'payroll_periods', ['period_code'], unique=False)
    op.create_index(op.f('ix_payroll_periods_status'), 'payroll_periods', ['status'], unique=False)

    # 2. Create payroll_runs
    op.create_table(
        'payroll_runs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('payroll_period_id', sa.BigInteger(), nullable=False),
        sa.Column('run_version', sa.BigInteger(), server_default='1', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='DRAFT', nullable=False),
        sa.Column('total_gross_earnings', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_employee_deductions', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_tax_tds', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_employee_pf', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_employer_pf', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_pt', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_net_pay', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_employer_cost', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('result_hash', sa.String(length=64), nullable=False),
        sa.Column('engine_version', sa.String(length=50), server_default='CALC-1.0.0', nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('approved_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payroll_period_id'], ['payroll_periods.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'payroll_period_id', 'run_version', name='uq_payroll_run_idempotency')
    )
    op.create_index(op.f('ix_payroll_runs_organization_id'), 'payroll_runs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_payroll_runs_payroll_period_id'), 'payroll_runs', ['payroll_period_id'], unique=False)
    op.create_index(op.f('ix_payroll_runs_status'), 'payroll_runs', ['status'], unique=False)

    # 3. Create payroll_run_items
    op.create_table(
        'payroll_run_items',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payroll_run_id', sa.BigInteger(), nullable=False),
        sa.Column('employee_id', sa.BigInteger(), nullable=False),
        sa.Column('calculation_run_id', sa.BigInteger(), nullable=True),
        sa.Column('calculation_snapshot_id', sa.BigInteger(), nullable=True),
        sa.Column('monthly_gross', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('basic_salary', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('hra', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('special_allowance', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('other_earnings', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('employee_pf', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('professional_tax', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('tds_deducted', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('other_deductions', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_employee_deductions', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('net_pay', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('employer_pf', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('employer_eps', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('employer_edli', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('employer_cost', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('days_worked', sa.Integer(), server_default='30', nullable=False),
        sa.Column('lop_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['calculation_run_id'], ['calculation_runs.id'], ),
        sa.ForeignKeyConstraint(['calculation_snapshot_id'], ['calculation_snapshots.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['payroll_run_id'], ['payroll_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('payroll_run_id', 'employee_id', name='uq_payroll_item_emp')
    )
    op.create_index(op.f('ix_payroll_run_items_employee_id'), 'payroll_run_items', ['employee_id'], unique=False)
    op.create_index(op.f('ix_payroll_run_items_payroll_run_id'), 'payroll_run_items', ['payroll_run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payroll_run_items_payroll_run_id'), table_name='payroll_run_items')
    op.drop_index(op.f('ix_payroll_run_items_employee_id'), table_name='payroll_run_items')
    op.drop_table('payroll_run_items')

    op.drop_index(op.f('ix_payroll_runs_status'), table_name='payroll_runs')
    op.drop_index(op.f('ix_payroll_runs_payroll_period_id'), table_name='payroll_runs')
    op.drop_index(op.f('ix_payroll_runs_organization_id'), table_name='payroll_runs')
    op.drop_table('payroll_runs')

    op.drop_index(op.f('ix_payroll_periods_status'), table_name='payroll_periods')
    op.drop_index(op.f('ix_payroll_periods_period_code'), table_name='payroll_periods')
    op.drop_index(op.f('ix_payroll_periods_organization_id'), table_name='payroll_periods')
    op.drop_index(op.f('ix_payroll_periods_financial_year'), table_name='payroll_periods')
    op.drop_table('payroll_periods')
