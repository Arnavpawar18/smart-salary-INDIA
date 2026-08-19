from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any


class AnomalySeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class AnomalyPolicy:
    """
    Configurable anomaly detection policy avoiding hardcoded thresholds.
    """

    percentage_threshold: Decimal = Decimal("0.25")  # e.g., 25% MoM variance
    absolute_threshold_rupees: Decimal = Decimal("25000.00")
    lookback_periods: int = 3
    severity: AnomalySeverity = AnomalySeverity.WARNING


@dataclass
class AnomalyReportDTO:
    is_anomaly: bool
    severity: AnomalySeverity
    field_name: str
    previous_value: Decimal
    current_value: Decimal
    percentage_delta: Decimal
    absolute_delta: Decimal
    explanation: str
    evidence: dict[str, Any]


class AnomalyDetectionEngine:
    """
    Dynamic Anomaly Detection Engine for payroll, payslips, and salary history.
    """

    @classmethod
    def evaluate_variance(
        cls,
        field_name: str,
        previous_value: Decimal,
        current_value: Decimal,
        policy: AnomalyPolicy | None = None,
    ) -> AnomalyReportDTO | None:
        pol = policy or AnomalyPolicy()
        abs_delta = abs(current_value - previous_value)

        pct_delta = Decimal("0.00")
        if previous_value > Decimal("0.00"):
            pct_delta = (abs_delta / previous_value).quantize(Decimal("0.0001"))

        # Trigger anomaly if BOTH or EITHER exceed depending on significance
        if pct_delta >= pol.percentage_threshold and abs_delta >= pol.absolute_threshold_rupees:
            severity = AnomalySeverity.HIGH if pct_delta >= Decimal("0.50") else pol.severity
            return AnomalyReportDTO(
                is_anomaly=True,
                severity=severity,
                field_name=field_name,
                previous_value=previous_value,
                current_value=current_value,
                percentage_delta=(pct_delta * Decimal("100.00")).quantize(Decimal("0.01")),
                absolute_delta=abs_delta,
                explanation=(
                    f"Noticeable variance detected in {field_name}: changed by "
                    f"{pct_delta * 100:.1f}% (₹{abs_delta}) compared with prior baseline."
                ),
                evidence={
                    "previous_value": str(previous_value),
                    "current_value": str(current_value),
                    "percentage_delta": str(pct_delta * 100),
                },
            )

        return None
