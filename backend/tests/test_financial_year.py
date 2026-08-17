from datetime import datetime

import pytest

from app.core.database import SessionLocal
from app.engine.common.errors import RuleNotFoundError
from app.presentation.financial_year import INDIA_TIMEZONE, FinancialYearResolver


def test_financial_year_boundary_logic():
    """Verify strict April 1 boundary logic in Asia/Kolkata timezone."""
    # 31 March 2026 23:59:59 IST -> FY 2025-26
    dt1 = datetime(2026, 3, 31, 23, 59, 59, tzinfo=INDIA_TIMEZONE)
    assert FinancialYearResolver.get_current_financial_year(dt1) == "2025-26"

    # 01 April 2026 00:00:01 IST -> FY 2026-27
    dt2 = datetime(2026, 4, 1, 0, 0, 1, tzinfo=INDIA_TIMEZONE)
    assert FinancialYearResolver.get_current_financial_year(dt2) == "2026-27"

    # 17 August 2026 IST -> FY 2026-27
    dt3 = datetime(2026, 8, 17, 16, 50, 0, tzinfo=INDIA_TIMEZONE)
    assert FinancialYearResolver.get_current_financial_year(dt3) == "2026-27"

    # 15 January 2027 IST -> FY 2026-27
    dt4 = datetime(2027, 1, 15, 12, 0, 0, tzinfo=INDIA_TIMEZONE)
    assert FinancialYearResolver.get_current_financial_year(dt4) == "2026-27"


def test_financial_year_supported_lookup():
    with SessionLocal() as db:
        years = FinancialYearResolver.validate_and_get_supported_years(db)
        assert "2024-25" in years
        assert "2025-26" in years
        assert "2026-27" in years

        # Ensure valid doesn't raise
        FinancialYearResolver.ensure_year_supported(db, "2025-26")

        # Unsupported year raises fail-closed error
        with pytest.raises(RuleNotFoundError):
            FinancialYearResolver.ensure_year_supported(db, "2099-00")
