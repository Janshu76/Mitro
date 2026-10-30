"""Secure comparison patterns retained as false-positive decoys for Mitro."""
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import LoanApplication

log = logging.getLogger("lendwise.safe")

def log_application_event(application_id: int, event: str) -> None:
    # SECURE DECOY: log only a surrogate ID and event; no customer identifiers or document data.
    log.info("application_event application_id=%s event=%s", application_id, event)

def find_owned_application(db: Session, application_id: int, authenticated_customer_id: int):
    # SECURE DECOY: caller passes a customer identity established by an auth layer;
    # ownership is enforced in the query rather than by an ID-only lookup.
    return db.scalar(select(LoanApplication).where(
        LoanApplication.id == application_id,
        LoanApplication.customer_id == authenticated_customer_id,
    ))
