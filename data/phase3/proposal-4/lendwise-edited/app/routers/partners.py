from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LoanAccount, PartnerEvent
from app.services.partner_gateway import send_disbursement

router = APIRouter(tags=["partners"])

@router.post("/partners/{partner}/disbursements")
def disburse(partner: str, loan_id: int, db: Session = Depends(get_db)):
    loan = db.get(LoanAccount, loan_id)
    if not loan:
        raise HTTPException(404, "Loan not found")
    receipt = send_disbursement(partner, loan.id, loan.principal)
    db.add(PartnerEvent(partner_name=partner, loan_id=loan.id, event_type="disbursement",
                        payload_summary=f"receipt={receipt['receipt_id']}; amount={loan.principal:.2f}"))
    db.commit()
    return {"loan_id": loan.id, "partner": partner, "accepted": receipt["accepted"], "receipt_id": receipt["receipt_id"]}
