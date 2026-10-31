from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.digital_lending_controls import (
    accept_complaint,
    record_personal_data_incident,
    request_cooling_off_exit,
)

router = APIRouter(tags=["customer protection"])


class ComplaintIn(BaseModel):
    customer_id: int
    description: str = Field(min_length=5, max_length=1000)


@router.post("/support/complaints", status_code=202)
def submit_complaint(body: ComplaintIn):
    # PLANTED ISSUE: no nodal officer routing, complaint identifier, or aging/escalation record.
    return accept_complaint(body.customer_id, body.description)


@router.post("/loans/{loan_id}/cooling-off-exit")
def cooling_off_exit(loan_id: int):
    # PLANTED ISSUE: digital-loan exit is rejected without checking the Board-set window
    # or computing principal plus proportionate APR.
    return request_cooling_off_exit(loan_id)


@router.post("/security/personal-data-incidents/{incident_id}", status_code=202)
def report_personal_data_incident(incident_id: str):
    # PLANTED ISSUE: incident is recorded but neither affected people nor the Board are notified.
    return record_personal_data_incident(incident_id)
