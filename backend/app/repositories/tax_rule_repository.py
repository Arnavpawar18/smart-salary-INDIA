
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.common.enums import TaxRegime
from app.engine.common.errors import RuleNotFoundError
from app.engine.common.hashing import compute_sha256_hash
from app.engine.dto.tax_dto import (
    TaxCessRuleDTO,
    TaxDeductionRuleDTO,
    TaxRebateRuleDTO,
    TaxRuleSet,
    TaxSlabRuleDTO,
    TaxSurchargeRuleDTO,
)
from app.models.tax import TaxPeriod, TaxRuleVersion


class TaxRuleRepository:
    """Hydrates immutable TaxRuleSet DTO from PostgreSQL with full statutory provenance."""

    def __init__(self, db: Session):
        self.db = db

    def get_tax_rule_set(self, financial_year: str, regime: TaxRegime) -> TaxRuleSet:
        stmt = (
            select(TaxRuleVersion)
            .join(TaxPeriod, TaxRuleVersion.tax_period_id == TaxPeriod.id)
            .where(
                TaxPeriod.financial_year == financial_year,
                TaxRuleVersion.regime == regime.value,
                TaxRuleVersion.status == "ACTIVE",
            )
        )
        trv: TaxRuleVersion | None = self.db.scalar(stmt)
        if not trv:
            raise RuleNotFoundError(
                f"No active statutory tax rule version found for Financial Year '{financial_year}' and regime '{regime.value}'."
            )

        slabs_dto = [
            TaxSlabRuleDTO(
                slab_order=s.slab_order,
                from_amount=s.from_amount,
                to_amount=s.to_amount,
                tax_rate=s.tax_rate,
            )
            for s in sorted(trv.slabs, key=lambda x: x.slab_order)
        ]

        rebates_dto = [
            TaxRebateRuleDTO(
                section_code=r.section,
                taxable_income_threshold=r.threshold_taxable_income,
                max_rebate_amount=r.max_rebate_amount,
                marginal_relief_applicable=True,
            )
            for r in trv.rebates
        ]

        deductions_dto = [
            TaxDeductionRuleDTO(
                deduction_code=d.section,
                deduction_name=d.name,
                max_limit=d.max_limit,
                regime_applicable=trv.regime,
                is_standard_deduction="16(ia)" in d.section or "Standard" in d.name,
            )
            for d in trv.deductions
        ]

        surcharges_dto = [
            TaxSurchargeRuleDTO(
                from_income=sc.from_income,
                to_income=sc.to_income,
                surcharge_rate=sc.surcharge_rate,
                marginal_relief_applicable=sc.is_marginal_relief_applicable,
            )
            for sc in trv.surcharges
        ]

        cess_dto = [
            TaxCessRuleDTO(
                cess_name=c.name,
                cess_rate=c.cess_rate,
            )
            for c in trv.cess_rules
        ]

        source_citation = f"CBDT / Income Tax Department (AY {financial_year[:4]}-{int(financial_year[:4])+1})"
        source_doc_hash = compute_sha256_hash(f"ITD-{financial_year}-{regime.value}")

        raw_rule_dict = {
            "version_code": trv.version_code,
            "financial_year": financial_year,
            "regime": regime.value,
            "slabs": [(s.slab_order, str(s.from_amount), str(s.to_amount), str(s.tax_rate)) for s in slabs_dto],
            "rebates": [(r.section_code, str(r.taxable_income_threshold), str(r.max_rebate_amount)) for r in rebates_dto],
            "deductions": [(d.deduction_code, str(d.max_limit)) for d in deductions_dto],
            "cess": [(c.cess_name, str(c.cess_rate)) for c in cess_dto],
        }
        rule_set_hash = compute_sha256_hash(raw_rule_dict)

        return TaxRuleSet(
            rule_version_code=trv.version_code,
            financial_year=financial_year,
            regime=regime,
            slabs=slabs_dto,
            rebates=rebates_dto,
            deductions=deductions_dto,
            surcharges=surcharges_dto,
            cess_rules=cess_dto,
            source_citation=source_citation,
            source_document_hash=source_doc_hash,
            rule_set_hash=rule_set_hash,
        )
