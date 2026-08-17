"""Add enterprise organizations and multi-tenant isolation

Revision ID: 003_add_enterprise_organizations
Revises: 002_add_user_sessions
Create Date: 2026-08-17 18:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '003_add_enterprise_organizations'
down_revision: str | None = '002_add_user_sessions'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('legal_name', sa.String(length=200), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('organization_code', sa.String(length=50), nullable=False),
        sa.Column('pan', sa.String(length=20), nullable=True),
        sa.Column('tan', sa.String(length=20), nullable=True),
        sa.Column('gstin', sa.String(length=30), nullable=True),
        sa.Column('primary_state_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['primary_state_id'], ['states.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_organization_code'), 'organizations', ['organization_code'], unique=True)
    op.create_index(op.f('ix_organizations_status'), 'organizations', ['status'], unique=False)

    # 2. Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('organization_id', sa.BigInteger(), nullable=False),
        sa.Column('role_id', sa.BigInteger(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organization_memberships_organization_id'), 'organization_memberships', ['organization_id'], unique=False)
    op.create_index(op.f('ix_organization_memberships_status'), 'organization_memberships', ['status'], unique=False)
    op.create_index(op.f('ix_organization_memberships_user_id'), 'organization_memberships', ['user_id'], unique=False)

    # 3. Add organization_id and lifecycle columns to employees, departments, job_roles
    op.add_column('departments', sa.Column('organization_id', sa.BigInteger(), nullable=True))
    op.add_column('departments', sa.Column('parent_department_id', sa.BigInteger(), nullable=True))
    op.add_column('departments', sa.Column('department_head_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_departments_organization_id'), 'departments', ['organization_id'], unique=False)
    op.create_foreign_key('fk_departments_organization_id', 'departments', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_departments_parent_department_id', 'departments', 'departments', ['parent_department_id'], ['id'])

    op.add_column('job_roles', sa.Column('organization_id', sa.BigInteger(), nullable=True))
    op.add_column('job_roles', sa.Column('grade', sa.String(length=20), nullable=True))
    op.add_column('job_roles', sa.Column('level', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_job_roles_organization_id'), 'job_roles', ['organization_id'], unique=False)
    op.create_foreign_key('fk_job_roles_organization_id', 'job_roles', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')

    op.add_column('employees', sa.Column('organization_id', sa.BigInteger(), nullable=True))
    op.add_column('employees', sa.Column('employment_status', sa.String(length=30), server_default='ACTIVE', nullable=False))
    op.add_column('employees', sa.Column('employment_type', sa.String(length=30), server_default='FULL_TIME', nullable=False))
    op.add_column('employees', sa.Column('date_of_exit', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('exit_reason', sa.String(length=255), nullable=True))
    op.add_column('employees', sa.Column('manager_id', sa.BigInteger(), nullable=True))
    op.create_index(op.f('ix_employees_organization_id'), 'employees', ['organization_id'], unique=False)
    op.create_index(op.f('ix_employees_employment_status'), 'employees', ['employment_status'], unique=False)
    op.create_foreign_key('fk_employees_organization_id', 'employees', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_employees_manager_id', 'employees', 'employees', ['manager_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_employees_manager_id', 'employees', type_='foreignkey')
    op.drop_constraint('fk_employees_organization_id', 'employees', type_='foreignkey')
    op.drop_index(op.f('ix_employees_employment_status'), table_name='employees')
    op.drop_index(op.f('ix_employees_organization_id'), table_name='employees')
    op.drop_column('employees', 'manager_id')
    op.drop_column('employees', 'exit_reason')
    op.drop_column('employees', 'date_of_exit')
    op.drop_column('employees', 'employment_type')
    op.drop_column('employees', 'employment_status')
    op.drop_column('employees', 'organization_id')

    op.drop_constraint('fk_job_roles_organization_id', 'job_roles', type_='foreignkey')
    op.drop_index(op.f('ix_job_roles_organization_id'), table_name='job_roles')
    op.drop_column('job_roles', 'level')
    op.drop_column('job_roles', 'grade')
    op.drop_column('job_roles', 'organization_id')

    op.drop_constraint('fk_departments_parent_department_id', 'departments', type_='foreignkey')
    op.drop_constraint('fk_departments_organization_id', 'departments', type_='foreignkey')
    op.drop_index(op.f('ix_departments_organization_id'), table_name='departments')
    op.drop_column('departments', 'department_head_id')
    op.drop_column('departments', 'parent_department_id')
    op.drop_column('departments', 'organization_id')

    op.drop_index(op.f('ix_organization_memberships_user_id'), table_name='organization_memberships')
    op.drop_index(op.f('ix_organization_memberships_status'), table_name='organization_memberships')
    op.drop_index(op.f('ix_organization_memberships_organization_id'), table_name='organization_memberships')
    op.drop_table('organization_memberships')

    op.drop_index(op.f('ix_organizations_status'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_organization_code'), table_name='organizations')
    op.drop_table('organizations')
