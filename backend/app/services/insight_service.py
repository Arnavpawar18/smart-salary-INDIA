from decimal import Decimal

from app.engine.dto.result_dto import VerifiedCalculationResult


class InsightService:
    """
    Generates deterministic educational tax and salary insights.
    Maintains strict 'not financial advice' boundaries.
    """

    DISCLAIMER = (
        "Educational Notice: SmartSalary provides computational and educational insights based on "
        "statutory income tax and provident fund rules. It does not provide personalized investment, "
        "tax-filing, or financial-advisory services."
    )

    @classmethod
    def generate_insights(cls, result: VerifiedCalculationResult) -> list[dict[str, str]]:
        insights = []

        # 1. Standard deduction insight
        if result.standard_deduction > 0:
            insights.append({
                "category": "Statutory Deduction",
                "title": "Section 16(ia) Standard Deduction",
                "content": f"You received a flat ₹{result.standard_deduction:,.2f} standard deduction reducing your taxable income directly.",
            })

        # 2. Section 87A rebate insight
        if result.section_87a_rebate > 0:
            insights.append({
                "category": "Tax Rebate",
                "title": "Full Section 87A Rebate Applied",
                "content": "Your net taxable income qualifies for Section 87A rebate, resulting in zero effective income tax liability.",
            })
        elif result.taxable_income <= Decimal("1200000.00") and result.regime.value == "NEW":
            insights.append({
                "category": "Tax Rebate Opportunity",
                "title": "Income within Rebate Threshold",
                "content": "Under FY 2025-26/2026-27 New Regime, taxable income up to ₹12 Lakh attracts zero income tax under Section 87A.",
            })

        # 3. Progressive tax bracket insight
        if result.slab_tax > Decimal("50000.00"):
            insights.append({
                "category": "Progressive Tax Slabs",
                "title": "Marginal Tax Bracket Awareness",
                "content": "Entering a higher tax slab applies higher percentage only to income within that specific bracket, never your entire salary.",
            })

        return insights
