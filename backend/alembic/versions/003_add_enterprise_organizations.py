"""Add enterprise organizations and multi-tenant isolation

Revision ID: 003_add_enterprise_organizations
Revises: 002_add_user_sessions
Create Date: 2026-08-17 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_add_enterprise_organizations"
down_revision: str | None = "002_add_user_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("organization_code", sa.String(length=50), nullable=False),
        sa.Column("pan", sa.String(length=20), nullable=True),
        sa.Column("tan", sa.String(length=20), nullable=True),
        sa.Column("gstin", sa.String(length=30), nullable=True),
        sa.Column("primary_state_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("timezone", sa.String(length=50), server_default="Asia/Kolkata", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["primary_state_id"],
            ["states.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_organization_code"), "organizations", ["organization_code"], unique=True)
    op.create_index(op.f("ix_organizations_status"), "organizations", ["status"], unique=False)

    # 2. Create organization_memberships table
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_organization_memberships_organization_id"),
        "organization_memberships",
        ["organization_id"],
        unique=False,
    )
    op.create_index(op.f("ix_organization_memberships_status"), "organization_memberships", ["status"], unique=False)
    op.create_index(op.f("ix_organization_memberships_user_id"), "organization_memberships", ["user_id"], unique=False)

    # 3. Add organization_id and lifecycle columns to employees, departments, job_roles
    with op.batch_alter_table("departments") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("parent_department_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("department_head_id", sa.BigInteger(), nullable=True))
        batch_op.create_index(batch_op.f("ix_departments_organization_id"), ["organization_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_departments_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key(
            "fk_departments_parent_department_id", "departments", ["parent_department_id"], ["id"]
        )

    with op.batch_alter_table("job_roles") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(sa.Column("grade", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("level", sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f("ix_job_roles_organization_id"), ["organization_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_job_roles_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.BigInteger(), nullable=True))
        batch_op.add_column(
            sa.Column("employment_status", sa.String(length=30), server_default="ACTIVE", nullable=False)
        )
        batch_op.add_column(
            sa.Column("employment_type", sa.String(length=30), server_default="FULL_TIME", nullable=False)
        )
        batch_op.add_column(sa.Column("date_of_exit", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("exit_reason", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("manager_id", sa.BigInteger(), nullable=True))
        batch_op.create_index(batch_op.f("ix_employees_organization_id"), ["organization_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_employees_employment_status"), ["employment_status"], unique=False)
        batch_op.create_foreign_key(
            "fk_employees_organization_id", "organizations", ["organization_id"], ["id"], ondelete="CASCADE"
        )
        batch_op.create_foreign_key("fk_employees_manager_id", "employees", ["manager_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_constraint("fk_employees_manager_id", type_="foreignkey")
        batch_op.drop_constraint("fk_employees_organization_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_employees_employment_status"))
        batch_op.drop_index(batch_op.f("ix_employees_organization_id"))
        batch_op.drop_column("manager_id")
        batch_op.drop_column("exit_reason")
        batch_op.drop_column("date_of_exit")
        batch_op.drop_column("employment_type")
        batch_op.drop_column("employment_status")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("job_roles") as batch_op:
        batch_op.drop_constraint("fk_job_roles_organization_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_job_roles_organization_id"))
        batch_op.drop_column("level")
        batch_op.drop_column("grade")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("departments") as batch_op:
        batch_op.drop_constraint("fk_departments_parent_department_id", type_="foreignkey")
        batch_op.drop_constraint("fk_departments_organization_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_departments_organization_id"))
        batch_op.drop_column("department_head_id")
        batch_op.drop_column("parent_department_id")
        batch_op.drop_column("organization_id")

    op.drop_index(op.f("ix_organization_memberships_user_id"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_status"), table_name="organization_memberships")
    op.drop_index(op.f("ix_organization_memberships_organization_id"), table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index(op.f("ix_organizations_status"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_organization_code"), table_name="organizations")
    op.drop_table("organizations")
