from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engine.common.enums import Gender
from app.engine.common.errors import ProfessionalTaxRuleNotConfiguredError
from app.engine.common.hashing import compute_sha256_hash
from app.engine.dto.pt_dto import PtRuleSet, PtSlabRuleDTO
from app.models.employee import State
from app.models.pt import ProfessionalTaxRuleVersion


class PtRuleRepository:
    """Hydrates immutable PtRuleSet DTO from PostgreSQL with state statutory provenance."""

    def __init__(self, db: Session):
        self.db = db

    def get_pt_rule_set(self, state_code: str) -> PtRuleSet:
        state = self.db.scalar(select(State).where(State.code == state_code))
        if not state:
            raise ProfessionalTaxRuleNotConfiguredError(f"State code '{state_code}' not recognized.")

        # Delhi is officially exempt from Professional Tax
        if state_code == "DL":
            return PtRuleSet(
                state_code="DL",
                state_name="Delhi",
                rule_version_code="PTRV-DL-EXEMPT",
                slabs=[
                    PtSlabRuleDTO(
                        slab_order=1,
                        from_monthly_salary=0,
                        to_monthly_salary=None,
                        monthly_tax_amount=0,
                        february_tax_amount=0,
                        gender_applicable=Gender.ALL,
                    )
                ],
                source_citation="Government of NCT of Delhi (No Professional Tax Levied)",
                source_document_hash=compute_sha256_hash("DELHI-PT-EXEMPT"),
                rule_set_hash=compute_sha256_hash("DELHI-PT-EXEMPT"),
            )

        stmt = select(ProfessionalTaxRuleVersion).where(
            ProfessionalTaxRuleVersion.state_id == state.id,
            ProfessionalTaxRuleVersion.status == "ACTIVE",
        )
        ptrv: Optional[ProfessionalTaxRuleVersion] = self.db.scalar(stmt)
        if not ptrv or not ptrv.slabs:
            raise ProfessionalTaxRuleNotConfiguredError(
                f"Professional Tax statutory rule is not verified/configured for state '{state.name}' ({state_code}). "
                "Calculation failed-closed to prevent unverified financial estimates."
            )

        slabs_dto = [
            PtSlabRuleDTO(
                slab_order=s.slab_order,
                from_monthly_salary=s.from_monthly_salary,
                to_monthly_salary=s.to_monthly_salary,
                monthly_tax_amount=s.monthly_tax_amount,
                february_tax_amount=s.february_tax_amount,
                gender_applicable=Gender(s.gender_applicable),
            )
            for s in sorted(ptrv.slabs, key=lambda x: x.slab_order)
        ]

        source_citation = f"Commercial Taxes Department / State Govt of {state.name}"
        source_doc_hash = compute_sha256_hash(f"PT-{state_code}-STATUTORY")
        raw_rule_dict = {
            "version_code": ptrv.version_code,
            "state_code": state_code,
            "slabs": [(s.slab_order, str(s.from_monthly_salary), str(s.monthly_tax_amount)) for s in slabs_dto],
        }
        rule_set_hash = compute_sha256_hash(raw_rule_dict)

        return PtRuleSet(
            state_code=state_code,
            state_name=state.name,
            rule_version_code=ptrv.version_code,
            slabs=slabs_dto,
            source_citation=source_citation,
            source_document_hash=source_doc_hash,
            rule_set_hash=rule_set_hash,
        )
