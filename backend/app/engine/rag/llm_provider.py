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

        # Deterministic grounded responses based on domain context
        if "87a" in lower_msg or "rebate" in lower_msg:
            content = (
                "### Section 87A Rebate Explanation\n\n"
                "**Short Answer:** Under the New Tax Regime (FY 2025-26 & FY 2026-27), Section 87A provides a full tax rebate for taxable income up to ₹7,00,000 (standard slab relief up to ₹25,000).\n\n"
                "**Statutory Rule Reference:** Section 87A of the Income Tax Act, 1961 (as amended by Finance Act).\n\n"
                "**Evidence:** In the New Regime, if your taxable income does not exceed the threshold, your net income tax liability is reduced to ₹0."
            )
        elif "pf" in lower_msg or "epf" in lower_msg:
            content = (
                "### Employee Provident Fund (EPF) Calculation\n\n"
                "**Short Answer:** Statutory employee EPF contribution is computed as 12% of your monthly Qualifying Basic Salary + DA, subject to a statutory statutory cap of ₹1,800/month (on ₹15,000 basic ceiling) or actual 12% if uncapped.\n\n"
                "**Statutory Rule Reference:** Employees' Provident Funds and Miscellaneous Provisions Act, 1952.\n\n"
                "**Evidence:** Verified against EPFO statutory guidelines."
            )
        elif "payslip" in lower_msg or "reconciliation" in lower_msg or "discrepancy" in lower_msg:
            content = (
                "### Payslip Reconciliation Analysis\n\n"
                "**Short Answer:** The payslip line items have been reconciled against the employer payroll run and statutory calculation snapshot.\n\n"
                "**Evidence:** The three-way reconciliation status indicates concordance across gross earnings and statutory deductions."
            )
        else:
            content = (
                "### SmartSalary Financial Assistant\n\n"
                "Based on your inquiry and authorized financial records, SmartSalary has evaluated your calculation and statutory profile.\n\n"
                "**Evidence:** Grounded in authoritative Phase 2 calculation snapshots and official Income Tax statutory rules."
            )

        return LLMResponse(
            content=content,
            model_name=self.model_name,
            tokens_used=len(content.split()),
            finish_reason="stop",
        )
