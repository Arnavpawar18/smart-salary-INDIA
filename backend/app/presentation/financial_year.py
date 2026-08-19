from datetime import date, datetime
from typing import NamedTuple
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.common.errors import RuleNotFoundError
from app.models.tax import TaxPeriod

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


class StatutoryPeriodContext(NamedTuple):
    financial_year: str
    tax_year: str
    assessment_year: str | None
    governing_act: str
    start_date: date
    end_date: date
    is_current: bool


class FinancialYearResolver:
    """
    Authoritatively determines Indian Financial Year & Tax Year based on Asia/Kolkata timezone.

    Canonical Directives (w.e.f. 1 April 2026):
    - FY 2026-27 onwards => Tax Year '2026-27' under Income-tax Act, 2025 (Assessment Year: N/A / Abolished)
    - FY 2025-26 & earlier => Previous Year under Income-tax Act, 1961 (Assessment Year: '2026-27')
    - Boundary: 01 Apr YYYY 00:00:00 to 31 Mar (YYYY+1) 23:59:59 IST
    """

    @classmethod
    def get_current_financial_year(cls, current_dt: datetime | None = None) -> str:
        if current_dt is None:
            now = datetime.now(INDIA_TIMEZONE)
        else:
            if current_dt.tzinfo is None:
                now = current_dt.replace(tzinfo=INDIA_TIMEZONE)
            else:
                now = current_dt.astimezone(INDIA_TIMEZONE)

        year = now.year
        month = now.month

        if month >= 4:
            start_year = year
            end_year_short = str(year + 1)[-2:]
        else:
            start_year = year - 1
            end_year_short = str(year)[-2:]

        return f"{start_year}-{end_year_short}"

    @classmethod
    def resolve_statutory_context(cls, financial_year: str) -> StatutoryPeriodContext:
        """
        Resolves the exact statutory legal framework (Income-tax Act 2025 vs 1961) for a given FY.
        """
        start_year = int(financial_year.split("-")[0])
        start_date = date(start_year, 4, 1)
        end_date = date(start_year + 1, 3, 31)

        if start_year >= 2026:
            return StatutoryPeriodContext(
                financial_year=financial_year,
                tax_year=financial_year,
                assessment_year=None,
                governing_act="INCOME_TAX_ACT_2025",
                start_date=start_date,
                end_date=end_date,
                is_current=True,
            )
        else:
            ay_start = start_year + 1
            ay_end_short = str(ay_start + 1)[-2:]
            return StatutoryPeriodContext(
                financial_year=financial_year,
                tax_year=f"PY_{financial_year}",
                assessment_year=f"{ay_start}-{ay_end_short}",
                governing_act="INCOME_TAX_ACT_1961",
                start_date=start_date,
                end_date=end_date,
                is_current=False,
            )

    @classmethod
    def validate_and_get_supported_years(cls, db: Session) -> list[str]:
        stmt = select(TaxPeriod.financial_year).order_by(TaxPeriod.start_date.desc())
        years = list(db.scalars(stmt).all())
        return years

    @classmethod
    def ensure_year_supported(cls, db: Session, financial_year: str) -> None:
        supported = cls.validate_and_get_supported_years(db)
        if financial_year not in supported:
            raise RuleNotFoundError(
                f"Financial Year '{financial_year}' is not supported or verified in SmartSalary. "
                f"Supported years: {', '.join(supported)}"
            )
