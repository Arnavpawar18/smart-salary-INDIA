from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.common.errors import RuleNotFoundError
from app.models.tax import TaxPeriod

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


class FinancialYearResolver:
    """
    Authoritatively determines Indian Financial Year based on Asia/Kolkata timezone.
    Boundary logic:
    - 01 Apr YYYY to 31 Mar (YYYY+1) => Financial Year 'YYYY-(YY+1)'
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
