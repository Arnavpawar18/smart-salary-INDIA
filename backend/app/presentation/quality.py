from enum import StrEnum


class CalculationQuality(StrEnum):
    DETAILED = "DETAILED"
    ESTIMATE = "ESTIMATE"
    INCOMPLETE = "INCOMPLETE"
    UNSUPPORTED = "UNSUPPORTED"


class QualityClassifier:
    """
    Deterministic classifier evaluating input completeness and statutory support.
    """

    @classmethod
    def classify(
        cls,
        is_quick_mode: bool,
        has_custom_components: bool,
        is_supported: bool,
    ) -> dict[str, str]:
        if not is_supported:
            return {
                "status": CalculationQuality.UNSUPPORTED.value,
                "badge_label": "Unsupported",
                "badge_class": "bg-rose-100 text-rose-800 border-rose-300",
                "aria_label": "Status: Unsupported calculation — rules not available",
                "description": "Selected financial year or state statutory rules could not be resolved.",
            }

        if is_quick_mode and not has_custom_components:
            return {
                "status": CalculationQuality.ESTIMATE.value,
                "badge_label": "Quick Estimate",
                "badge_class": "bg-amber-100 text-amber-800 border-amber-300",
                "aria_label": "Status: Quick estimate — standard salary assumptions applied",
                "description": "Quick estimate based on standard salary assumptions. Add custom salary components for an exact payroll breakdown.",
            }

        return {
            "status": CalculationQuality.DETAILED.value,
            "badge_label": "Detailed Calculation",
            "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300",
            "aria_label": "Status: Detailed calculation — high input completeness",
            "description": "Detailed calculation computed using explicit user-supplied component breakdown.",
        }
