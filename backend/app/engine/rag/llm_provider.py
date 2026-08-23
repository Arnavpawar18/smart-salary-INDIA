import re
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
    Formats authoritative calculation context and official evidence without independently calculating or inventing numbers.
    """

    def __init__(self, model_name: str = "smartsalary-mock-rag-v1"):
        self.model_name = model_name

    def _extract_context(self, messages: list[LLMMessage]) -> dict[str, str]:
        context_data: dict[str, str] = {}
        for m in messages:
            if "ACTIVE IMMUTABLE CALCULATION CONTEXT" in m.content:
                lines = m.content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("- Annual Gross CTC:"):
                        context_data["gross"] = line.replace("- Annual Gross CTC:", "").strip()
                    elif line.startswith("- Net Taxable Income:"):
                        context_data["taxable"] = line.replace("- Net Taxable Income:", "").strip()
                    elif line.startswith("- Total Annual Tax:"):
                        context_data["tax"] = line.replace("- Total Annual Tax:", "").strip()
                    elif line.startswith("- Section 87A Rebate:"):
                        context_data["rebate"] = line.replace("- Section 87A Rebate:", "").strip()
                    elif line.startswith("- Annual EPF:"):
                        context_data["epf"] = line.replace("- Annual EPF:", "").strip()
                    elif line.startswith("- Annual Professional Tax:"):
                        context_data["pt"] = line.replace("- Annual Professional Tax:", "").strip()
                    elif line.startswith("- Annual Take-Home:"):
                        context_data["annual_take_home"] = line.replace("- Annual Take-Home:", "").strip()
                    elif line.startswith("- Monthly Take-Home:"):
                        context_data["monthly_take_home"] = line.replace("- Monthly Take-Home:", "").strip()
                    elif line.startswith("- Financial Year:"):
                        m_fy = re.search(r"Financial Year:\s*([^|]+)", line)
                        if m_fy:
                            context_data["fy"] = m_fy.group(1).strip()
                        m_reg = re.search(r"Regime:\s*([^|]+)", line)
                        if m_reg:
                            context_data["regime"] = m_reg.group(1).strip()
                        m_st = re.search(r"State:\s*(\S+)", line)
                        if m_st:
                            context_data["state"] = m_st.group(1).strip()
        return context_data

    def generate(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        user_msg = next((m.content for m in reversed(messages) if m.role == "user"), "")
        lower_msg = user_msg.lower()
        ctx = self._extract_context(messages)

        has_calc = bool(ctx.get("gross"))

        # Deterministic grounded responses following standard structure:
        # ### Short Answer, ### Calculation, ### Why, ### Applicable Rule, ### Official Source, ### What this means for you
        if "87a" in lower_msg or "rebate" in lower_msg:
            if has_calc:
                rebate_val = ctx.get("rebate", "0")
                tax_val = ctx.get("tax", "0")
                content = (
                    "### Short Answer\n"
                    f"Under the New Tax Regime, Section 87A provides a statutory rebate on your taxable income, giving an applied rebate of ₹{rebate_val} for your calculation.\n\n"
                    "### Calculation\n"
                    f"Taxable Income ₹{ctx.get('taxable', '0')} ➔ Net Income Tax Liability ₹{tax_val} (Section 87A Rebate ₹{rebate_val})\n\n"
                    "### Why\n"
                    "The rebate applies automatically based on statutory limits defined by the Central Government in the Finance Act.\n\n"
                    "### Applicable Rule\n"
                    "Section 87A of the Income-tax Act, 1961.\n\n"
                    "### Official Source\n"
                    "Income Tax Department / Central Board of Direct Taxes (CBDT Gazette).\n\n"
                    "### What this means for you\n"
                    f"Your total annual tax liability after statutory rebate is ₹{tax_val}."
                )
            else:
                content = (
                    "### Short Answer\n"
                    "Under the New Tax Regime (Section 115BAC), Section 87A provides a 100% tax rebate for taxable income up to ₹7,00,000 (extended in later Finance Acts).\n\n"
                    "### Calculation\n"
                    "Taxable Income ≤ ₹7,00,000 ➔ Slab Tax ₹25,000 − Section 87A Rebate ₹25,000 = **Net Tax ₹0**\n\n"
                    "### Why\n"
                    "The rebate is designed by the Central Government to provide complete income tax relief to middle-income salary earners.\n\n"
                    "### Applicable Rule\n"
                    "Section 87A of the Income-tax Act, 1961 (amended by Finance Act).\n\n"
                    "### Official Source\n"
                    "Income Tax Department / Central Board of Direct Taxes (CBDT Gazette).\n\n"
                    "### What this means for you\n"
                    "If your net taxable income remains within the statutory rebate threshold, your final estimated income tax liability is ₹0."
                )
        elif "pf" in lower_msg or "epf" in lower_msg:
            if has_calc:
                epf_val = ctx.get("epf", "0")
                content = (
                    "### Short Answer\n"
                    f"Your Employee Provident Fund (EPF) deduction is ₹{epf_val} annually, computed at 12% of your eligible statutory wage base.\n\n"
                    "### Calculation\n"
                    f"12% of eligible monthly EPF wage base (annualized to ₹{epf_val}).\n\n"
                    "### Why\n"
                    "EPF is a mandatory statutory retirement savings program governed by Central law for covered establishments.\n\n"
                    "### Applicable Rule\n"
                    "Employees' Provident Funds and Miscellaneous Provisions Act, 1952 (EPFO Rule Set).\n\n"
                    "### Official Source\n"
                    "Employees' Provident Fund Organisation (EPFO India) Official Gazette.\n\n"
                    "### What this means for you\n"
                    f"₹{epf_val} is credited annually to your EPFO account and matched by your employer's statutory contribution."
                )
            else:
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
        elif "pt" in lower_msg or "professional tax" in lower_msg:
            if has_calc:
                pt_val = ctx.get("pt", "0")
                st = ctx.get("state", "KA")
                content = (
                    "### Short Answer\n"
                    f"Your state Professional Tax deduction is ₹{pt_val} annually for {st}.\n\n"
                    "### Calculation\n"
                    f"Calculated according to the statutory slab schedule of {st} Professional Tax Act.\n\n"
                    "### Why\n"
                    "Professional Tax is levied by State Governments under Article 276 of the Constitution of India.\n\n"
                    "### Applicable Rule\n"
                    f"State Professional Tax Schedule ({st}).\n\n"
                    "### Official Source\n"
                    "State Commercial Taxes Department Gazette.\n\n"
                    "### What this means for you\n"
                    f"A total of ₹{pt_val} is deducted across the year to satisfy state statutory compliance."
                )
            else:
                content = (
                    "### Short Answer\n"
                    "Professional Tax is a state-level statutory deduction levied on salaried income under Article 276 of the Constitution of India.\n\n"
                    "### Calculation\n"
                    "Varies by State slab (e.g. Karnataka: ₹200/month for gross ≥ ₹25,000; Maharashtra: ₹200/month, ₹300 in February).\n\n"
                    "### Why\n"
                    "Mandated by individual State Governments for municipal development and local governance.\n\n"
                    "### Applicable Rule\n"
                    "State Professions, Trades, Callings and Employments Act.\n\n"
                    "### Official Source\n"
                    "State Commercial Taxes Department.\n\n"
                    "### What this means for you\n"
                    "Professional tax is deducted from your gross earnings before net take-home is disbursed."
                )
        elif "tax" in lower_msg or "take-home" in lower_msg or "take home" in lower_msg or "salary" in lower_msg or "why is my" in lower_msg:
            if has_calc:
                gross = ctx.get("gross", "0")
                tax = ctx.get("tax", "0")
                epf = ctx.get("epf", "0")
                pt = ctx.get("pt", "0")
                take_home = ctx.get("annual_take_home", "0")
                monthly_th = ctx.get("monthly_take_home", "0")
                reg = ctx.get("regime", "NEW")
                fy = ctx.get("fy", "2025-26")
                content = (
                    "### Short Answer\n"
                    f"For an annual CTC of ₹{gross} under the {reg} regime (FY {fy}), your net take-home is ₹{take_home}/year (approx ₹{monthly_th}/month).\n\n"
                    "### Calculation\n"
                    f"Gross Earnings: ₹{gross}\n"
                    f"− Income Tax Liability: ₹{tax}\n"
                    f"− Employee EPF: ₹{epf}\n"
                    f"− Professional Tax: ₹{pt}\n"
                    f"= **Net Take-Home Pay: ₹{take_home}**\n\n"
                    "### Why\n"
                    "Your take-home is calculated deterministically by deducting statutory Central taxes, retirement EPF, and State PT from your gross salary.\n\n"
                    "### Applicable Rule\n"
                    "Income-tax Act, 1961 (Sec 115BAC), EPFO Act 1952, and State PT Regulations.\n\n"
                    "### Official Source\n"
                    "Central Board of Direct Taxes (CBDT) & EPFO India.\n\n"
                    "### What this means for you\n"
                    f"Your verified monthly in-hand credit is ₹{monthly_th}."
                )
            else:
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

