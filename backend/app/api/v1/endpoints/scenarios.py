from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.engine.common.enums import TaxRegime
from app.services.scenario_service import ScenarioService

router = APIRouter()


class WhatIfRequest(BaseModel):
    base_salary: Decimal = Field(gt=0)
    financial_year: str = Field(default="2025-26")
    state_code: str = Field(default="KA")
    regime: str = Field(default="NEW")
    raise_percentages: list[Decimal] | None = Field(default=[Decimal("5"), Decimal("10"), Decimal("20")])


@router.post("/what-if")
def calculate_what_if_raise(
    req: WhatIfRequest,
    db: Session = Depends(get_db),
):
    """Simulate incremental salary raises (+5%, +10%, +20%) and marginal take-home retention."""
    try:
        service = ScenarioService(db)
        regime_enum = TaxRegime(req.regime.upper())
        result = service.calculate_what_if_raises(
            base_salary=req.base_salary,
            financial_year=req.financial_year,
            state_code=req.state_code.upper(),
            regime=regime_enum,
            raise_percentages=req.raise_percentages or [Decimal("5"), Decimal("10"), Decimal("20")],
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
