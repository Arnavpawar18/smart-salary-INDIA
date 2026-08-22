from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model_name: str
    tokens_used: int = 0
    finish_reason: str = "stop"
    raw_response: dict | None = None


class LLMProvider(Protocol):
    """Abstract protocol for pluggable LLM integrations."""

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generates an LLM completion for the given conversation messages."""
        ...


class MockDevLLMProvider:
    """
    Deterministic Development LLM Provider.
    Produces evidence-grounded responses without requiring live external API keys.
    """

    def __init__(self, model_name: str = "smartsalary-mock-rag-v1"):
        self.model_name = model_name

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        lower_msg = user_msg.lower()

        # Deterministic grounded responses following standard structure:
        # ### Short Answer, ### Calculation, ### Why, ### Applicable Rule, ### Official Source, ### What this means for you
        if "87a" in lower_msg or "rebate" in lower_msg:
            content = (
                "### Short Answer\n"
                "Under the New Tax Regime (Section 115BAC), Section 87A provides a 100% tax rebate for taxable income up to ₹7,00,000.\n\n"
                "### Calculation\n"
                "Taxable Income ≤ ₹7,00,000 ➔ Slab Tax ₹25,000 − Section 87A Rebate ₹25,000 = **Net Tax ₹0**\n\n"
                "### Why\n"
                "The rebate is designed by the Central Government to provide complete income tax relief to middle-income salary earners.\n\n"
                "### Applicable Rule\n"
                "Section 87A of the Income-tax Act, 1961 (amended by Finance Act).\n\n"
                "### Official Source\n"
                "Income Tax Department / Central Board of Direct Taxes (CBDT Gazette).\n\n"
                "### What this means for you\n"
                "If your net taxable income remains within ₹7,00,000, your final estimated income tax liability is ₹0."
            )
        elif "pf" in lower_msg or "epf" in lower_msg:
            content = (
                "### Short Answer\n"
                "Your Employee Provident Fund (EPF) deduction is 12% of your eligible basic salary.\n\n"
                "### Calculation\n"
                "12% of eligible monthly EPF wage base (subject to the statutory ₹15,000 ceiling: ₹1,800/month, or actual 12% if uncapped).\n\n"
                "### Why\n"
                "EPF is a mandatory statutory retirement savings program governed by Central law for covered establishments.\n\n"
                "### Applicable Rule\n"
                "Employees' Provident Funds and Miscellaneous Provisions Act, 1952 (EPFO Rule Set).\n\n"
                "### Official Source\n"
                "Employees' Provident Fund Organisation (EPFO India) Official Gazette.\n\n"
                "### What this means for you\n"
                "This deduction is credited directly to your universal provident fund account and matched by your employer's statutory contribution."
            )
        elif "tax" in lower_msg or "take-home" in lower_msg or "take home" in lower_msg or "salary" in lower_msg:
            content = (
                "### Short Answer\n"
                "Your take-home salary is computed deterministically by subtracting statutory employee deductions (Income Tax TDS, EPF, and State Professional Tax) from your gross earnings.\n\n"
                "### Calculation\n"
                "Gross Salary − Employee EPF (12%) − State Professional Tax − Income Tax TDS = **Net Take-Home Pay**\n\n"
                "### Why\n"
                "Statutory deductions are mandated by Central and State legislations and computed on your exact salary parameters.\n\n"
                "### Applicable Rule\n"
                "Central Income Tax Act, 1961 (Sec 115BAC), EPFO Act 1952, and State Professional Tax Schedule.\n\n"
                "### Official Source\n"
                "CBDT Income Tax Gazette & State Commercial Taxes Department.\n\n"
                "### What this means for you\n"
                "Every rupee deducted from your salary is accounted for with an immutable audit hash and legal rule lineage."
            )
        elif "payslip" in lower_msg or "reconciliation" in lower_msg or "discrepancy" in lower_msg:
            content = (
                "### Short Answer\n"
                "The payslip line items have been verified against the employer payroll run and statutory calculation snapshot.\n\n"
                "### Calculation\n"
                "Three-way cross-verification: Employee Input ↔ Payroll Batch Record ↔ Immutable Snapshot Hash.\n\n"
                "### Why\n"
                "Reconciliation ensures zero variance between employer payroll records, employee deductions, and government deposits.\n\n"
                "### Applicable Rule\n"
                "Payment of Wages Act, 1936 & IT Rules 1962 (Form 16 / TDS reconciliation).\n\n"
                "### Official Source\n"
                "Ministry of Labour & Employment and CBDT.\n\n"
                "### What this means for you\n"
                "Your payslip is cryptographically verified and ready for tax compliance and loan documentation."
            )
        else:
            content = (
                "### Short Answer\n"
                "SmartSalary has analyzed your inquiry against your active calculation snapshot and official statutory guidelines.\n\n"
                "### Calculation\n"
                "Evaluated using active AY 2026-27 statutory rules and your authorized calculation parameters.\n\n"
                "### Why\n"
                "SmartSalary operates on a strict principle: Code Calculates, Laws Authorize, AI Explains.\n\n"
                "### Applicable Rule\n"
                "Income-tax Act, 1961 & EPFO Statutory Schedules.\n\n"
                "### Official Source\n"
                "Official Gazettes of India.\n\n"
                "### What this means for you\n"
                "All figures and explanations are grounded in verified legislation with zero mathematical hallucinations."
            )

        return LLMResponse(
            content=content,
            model_name=self.model_name,
            tokens_used=len(content.split()),
            finish_reason="stop",
        )
