from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.auth import User
    from app.models.calculation import CalculationRun
    from app.models.salary import IncomeSource, SalaryRecord


class State(Base, TimestampMixin):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_union_territory: Mapped[bool] = mapped_column(default=False, nullable=False)

    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="state")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="department")


class JobRole(Base, TimestampMixin):
    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="job_role")


class Employee(Base, TimestampMixin):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Enforce 0..1 relationship with User at database level: user_id is UNIQUE and nullable
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_of_joining: Mapped[date] = mapped_column(Date, nullable=False)

    department_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("departments.id"), nullable=True)
    job_role_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("job_roles.id"), nullable=True)
    state_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("states.id"), nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="employee")
    department: Mapped[Optional["Department"]] = relationship("Department", back_populates="employees")
    job_role: Mapped[Optional["JobRole"]] = relationship("JobRole", back_populates="employees")
    state: Mapped[Optional["State"]] = relationship("State", back_populates="employees")

    # 1..1 with TaxpayerProfile enforced by UNIQUE constraint on taxpayer_profiles.employee_id
    taxpayer_profile: Mapped[Optional["TaxpayerProfile"]] = relationship("TaxpayerProfile", back_populates="employee", uselist=False)
    salary_records: Mapped[list["SalaryRecord"]] = relationship("SalaryRecord", back_populates="employee")
    income_sources: Mapped[list["IncomeSource"]] = relationship("IncomeSource", back_populates="employee")
    calculation_runs: Mapped[list["CalculationRun"]] = relationship("CalculationRun", back_populates="employee")


class TaxpayerProfile(Base, TimestampMixin):
    __tablename__ = "taxpayer_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Enforce strict 1..1 with Employee at DB level (UNIQUE + NOT NULL)
    employee_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False)
    pan: Mapped[str | None] = mapped_column(String(10), unique=True, index=True, nullable=True)
    residential_status: Mapped[str] = mapped_column(String(50), default="RESIDENT", nullable=False)
    preferred_regime: Mapped[str] = mapped_column(String(10), default="NEW", nullable=False)  # OLD or NEW
    is_senior_citizen: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_super_senior_citizen: Mapped[bool] = mapped_column(default=False, nullable=False)

    employee: Mapped["Employee"] = relationship("Employee", back_populates="taxpayer_profile")
