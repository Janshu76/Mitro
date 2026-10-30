from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LoanAccount, Repayment
from app.schemas import RepaymentIn

router = APIRouter(tags=["servicing"])

@router.post("/loans/{loan_id}/repayments", status_code=201)
def post_repayment(loan_id: int, body: RepaymentIn, db: Session = Depends(get_db)):
    loan = db.get(LoanAccount, loan_id)
    if not loan:
        raise HTTPException(404, "Loan not found")
    if body.amount > loan.outstanding:
        raise HTTPException(400, "Repayment exceeds outstanding balance")
    loan.outstanding -= body.amount
    if loan.outstanding == 0:
        loan.status = "closed"
    repayment = Repayment(loan_id=loan.id, amount=body.amount, reference=body.reference)
    db.add(repayment)
    db.commit()
    return {"loan_id": loan.id, "outstanding": loan.outstanding, "status": loan.status}

@router.get("/support/customers/{customer_id}")
def support_customer(customer_id: int, db: Session = Depends(get_db)):
    loans = db.scalars(select(LoanAccount).where(LoanAccount.customer_id == customer_id)).all()
    if not loans:
        raise HTTPException(404, "Customer or loans not found")
    return {"customer_id": customer_id,
            "loans": [{"loan_id": loan.id, "principal": loan.principal,
                       "outstanding": loan.outstanding, "status": loan.status} for loan in loans]}
