import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Customer, LoanApplication, LoanAccount
from app.schemas import ApplicationIn, LegacyImportIn
from app.services.kyc_provider import verify_identity
from app.services.credit_policy import score_application

router = APIRouter(tags=["applications"])
log = logging.getLogger("lendwise.applications")

@router.post("/applications", status_code=201)
def create_application(body: ApplicationIn, db: Session = Depends(get_db)):
    # SECURE DECOY: this path checks consent before storing or sharing the record.
    if not body.consent:
        raise HTTPException(400, "Customer consent is required for this demo flow")
    customer = Customer(full_name=body.full_name, phone=body.phone, email=body.email,
                        pan_last4=body.pan_last4, date_of_birth=body.date_of_birth,
                        full_address=body.full_address, employer_name=body.employer_name,
                        bank_account_number=body.bank_account_number, consent_status="recorded")
    db.add(customer)
    db.flush()
    result = verify_identity(customer.full_name, customer.pan_last4)
    application = LoanApplication(customer_id=customer.id, requested_amount=body.requested_amount,
                                  purpose=body.purpose, status="kyc_pending" if not result["verified"] else "submitted")
    db.add(application)
    db.commit()
    db.refresh(application)
    # PLANTED ISSUE: unnecessary sensitive fields are included in application logs.
    log.info("application_created id=%s phone=%s pan_last4=%s", application.id, customer.phone, customer.pan_last4)
    return {"application_id": application.id, "status": application.status, "kyc_status": result["status"]}

@router.post("/applications/legacy-import", status_code=201)
def import_legacy_application(body: LegacyImportIn, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(400, "Customer consent is required for this import")
    customer = Customer(full_name=body.full_name, phone=body.phone, pan_last4=body.pan_last4,
                        consent_status="unknown")
    db.add(customer)
    db.flush()
    application = LoanApplication(customer_id=customer.id, requested_amount=body.requested_amount,
                                  purpose=body.purpose, status="submitted")
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"application_id": application.id, "status": application.status}

@router.post("/applications/{application_id}/evaluate")
def evaluate_application(application_id: int, db: Session = Depends(get_db)):
    application = db.get(LoanApplication, application_id)
    if not application:
        raise HTTPException(404, "Application not found")
    score, approved, reason = score_application(application.requested_amount, application.purpose)
    application.risk_score = score
    application.status = "approved" if approved else "declined"
    application.decision_reason = reason
    if approved:
        db.add(LoanAccount(application_id=application.id, customer_id=application.customer_id,
                           principal=application.requested_amount, outstanding=application.requested_amount))
    db.commit()
    return {"application_id": application.id, "status": application.status, "score": score, "reason": reason}

@router.get("/applications/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    row = db.get(LoanApplication, application_id)
    if not row:
        raise HTTPException(404, "Application not found")
    return {"id": row.id, "customer_id": row.customer_id, "amount": row.requested_amount,
            "purpose": row.purpose, "status": row.status, "risk_score": row.risk_score}
