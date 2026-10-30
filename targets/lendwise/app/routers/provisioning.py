"""Synthetic ECL route used by the Mitro DLG regression demo."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.provisioning import required_ecl

router = APIRouter(tags=["provisioning"])

class EclRequest(BaseModel):
    stage: str = Field(pattern=r"^stage_[123]$")
    gross_ecl: float = Field(ge=0)
    stage_allocated_dlg_cover: float = Field(ge=0)
    invocation_amount: float = Field(ge=0)

@router.post("/provisioning/ecl")
def calculate_stage_ecl(body: EclRequest):
    try:
        required = required_ecl(body.gross_ecl, body.stage_allocated_dlg_cover, body.invocation_amount)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"stage": body.stage, "required_ecl": required,
            "demo_note": "Synthetic stage-level example; not an accounting or regulatory determination."}
