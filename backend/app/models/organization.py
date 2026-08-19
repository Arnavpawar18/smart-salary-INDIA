from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import Role, User
    from app.models.employee import Department, Employee, JobRole, State


class Organization(Base, TimestampMixin):
    """
    Enterprise Tenant entity.
    Statuses: PENDING_SETUP, ACTIVE, SUSPENDED, ARCHIVED
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    legal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    organization_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Sensitive corporate identifiers (masked/restricted in UI)
    pan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tan: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(30), nullable=True)

    primary_state_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("states.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)

    # Relationships
    primary_state: Mapped[Optional["State"]] = relationship("State")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="organization")
    departments: Mapped[list["Department"]] = relationship("Department", back_populates="organization")
    job_roles: Mapped[list["JobRole"]] = relationship("JobRole", back_populates="organization")


class OrganizationMembership(Base, TimestampMixin):
    """
    Explicit user membership and role assignment within an organization.
    Statuses: ACTIVE, INACTIVE, INVITED
    """

    __tablename__ = "organization_memberships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    joined_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")
    role: Mapped["Role"] = relationship("Role")
