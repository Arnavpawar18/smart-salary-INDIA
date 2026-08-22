"""Add compliance and tax declarations tables: tax_declarations, tax_declaration_items, statutory_compliance_events

Revision ID: 005_add_tax_declarations_compliance
Revises: 004_add_payroll_core
Create Date: 2026-08-17 18:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_add_tax_declarations"
down_revision: str | None = "004_add_payroll_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create tax_declarations
    op.create_table(
        "tax_declarations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("financial_year", sa.String(length=20), nullable=False),
        sa.Column("regime", sa.String(length=10), server_default="NEW", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="DRAFT", nullable=False),
        sa.Column(
            "total_declared_deductions", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False
        ),
        sa.Column(
            "total_verified_deductions", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False
        ),
        sa.Column(
            "projected_annual_liability", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False
        ),
        sa.Column(
            "planned_monthly_withholding", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False
        ),
        sa.Column("actual_tds_deducted_ytd", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.BigInteger(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "financial_year", "regime", name="uq_tax_declaration_emp_fy_regime"),
    )
    op.create_index(op.f("ix_tax_declarations_employee_id"), "tax_declarations", ["employee_id"], unique=False)
    op.create_index(op.f("ix_tax_declarations_financial_year"), "tax_declarations", ["financial_year"], unique=False)
    op.create_index(op.f("ix_tax_declarations_organization_id"), "tax_declarations", ["organization_id"], unique=False)
    op.create_index(op.f("ix_tax_declarations_status"), "tax_declarations", ["status"], unique=False)

    # 2. Create tax_declaration_items
    op.create_table(
        "tax_declaration_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("declaration_id", sa.BigInteger(), nullable=False),
        sa.Column("section_code", sa.String(length=50), nullable=False),
        sa.Column("category_name", sa.String(length=100), nullable=False),
        sa.Column("declared_amount", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("verified_amount", sa.Numeric(precision=18, scale=2), server_default="0.00", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["declaration_id"], ["tax_declarations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tax_declaration_items_declaration_id"), "tax_declaration_items", ["declaration_id"], unique=False
    )

    # 3. Create statutory_compliance_events
    op.create_table(
        "statutory_compliance_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("financial_year", sa.String(length=20), nullable=False),
        sa.Column("period_label", sa.String(length=50), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("acknowledgement_number", sa.String(length=100), nullable=True),
        sa.Column("meta_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_statutory_compliance_events_organization_id"),
        "statutory_compliance_events",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_statutory_compliance_events_organization_id"), table_name="statutory_compliance_events")
    op.drop_table("statutory_compliance_events")

    op.drop_index(op.f("ix_tax_declaration_items_declaration_id"), table_name="tax_declaration_items")
    op.drop_table("tax_declaration_items")

    op.drop_index(op.f("ix_tax_declarations_status"), table_name="tax_declarations")
    op.drop_index(op.f("ix_tax_declarations_organization_id"), table_name="tax_declarations")
    op.drop_index(op.f("ix_tax_declarations_financial_year"), table_name="tax_declarations")
    op.drop_index(op.f("ix_tax_declarations_employee_id"), table_name="tax_declarations")
    op.drop_table("tax_declarations")
