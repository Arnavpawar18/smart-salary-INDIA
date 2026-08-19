from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ComponentTolerance:
    absolute_tolerance_rupees: Decimal
    relative_tolerance_pct: Decimal  # e.g., Decimal("0.001") for 0.1%
    is_critical_on_exceed: bool


class ReconciliationTolerancePolicy:
    """
    Multi-Tier Reconciliation Tolerance Policy.
    Defines distinct absolute and relative variances for financial fields.
    """

    # Field-specific policies
    POLICIES = {
        # Gross salary allows up to ₹10 or 0.1% rounding variance before warning
        "gross_earnings": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("10.00"),
            relative_tolerance_pct=Decimal("0.001"),
            is_critical_on_exceed=True,
        ),
        # Basic and HRA allow ₹5 rounding
        "basic": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("5.00"),
            relative_tolerance_pct=Decimal("0.001"),
            is_critical_on_exceed=True,
        ),
        "hra": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("5.00"),
            relative_tolerance_pct=Decimal("0.001"),
            is_critical_on_exceed=True,
        ),
        # EPF allows ₹1 rounding variance; statutory under-deduction is critical
        "employee_epf": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("1.00"),
            relative_tolerance_pct=Decimal("0.0"),
            is_critical_on_exceed=True,
        ),
        # Professional Tax is strict statutory schedule (₹0 exact match)
        "professional_tax": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("0.00"),
            relative_tolerance_pct=Decimal("0.0"),
            is_critical_on_exceed=True,
        ),
        # TDS allows monthly withholding projection rounding up to ₹5
        "tds": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("5.00"),
            relative_tolerance_pct=Decimal("0.005"),
            is_critical_on_exceed=True,
        ),
        # Net Pay allows up to ₹2 rounding
        "net_pay": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("2.00"),
            relative_tolerance_pct=Decimal("0.0"),
            is_critical_on_exceed=True,
        ),
        # Total Deductions allows up to ₹2 rounding
        "total_deductions": ComponentTolerance(
            absolute_tolerance_rupees=Decimal("2.00"),
            relative_tolerance_pct=Decimal("0.0"),
            is_critical_on_exceed=True,
        ),
    }

    DEFAULT_POLICY = ComponentTolerance(
        absolute_tolerance_rupees=Decimal("2.00"),
        relative_tolerance_pct=Decimal("0.0"),
        is_critical_on_exceed=False,
    )

    @classmethod
    def get_tolerance(cls, field_name: str) -> ComponentTolerance:
        return cls.POLICIES.get(field_name, cls.DEFAULT_POLICY)

    @classmethod
    def evaluate_difference(cls, field_name: str, actual: Decimal, expected: Decimal) -> tuple[str, Decimal]:
        """
        Evaluates difference between actual (payslip) and expected (payroll/statutory).
        Returns:
            (status: "EXACT" | "TOLERABLE_ROUNDING" | "CRITICAL_MISMATCH", delta: Decimal)
        """
        delta = abs(actual - expected)
        if delta == Decimal("0.00"):
            return "EXACT", delta

        tol = cls.get_tolerance(field_name)

        # Check absolute threshold
        if delta <= tol.absolute_tolerance_rupees:
            return "TOLERABLE_ROUNDING", delta

        # Check relative threshold if expected > 0
        if expected > Decimal("0.00") and tol.relative_tolerance_pct > Decimal("0.0"):
            rel_diff = delta / expected
            if rel_diff <= tol.relative_tolerance_pct:
                return "TOLERABLE_ROUNDING", delta

        return "CRITICAL_MISMATCH", delta
