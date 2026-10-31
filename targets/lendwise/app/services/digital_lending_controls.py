"""Deliberately incomplete controls used as Mitro engineering review fixtures."""


def build_incomplete_kfs(principal: float) -> dict:
    """PLANTED ISSUE: this offer lacks APR, fees, cooling-off and grievance details."""
    return {
        "principal": principal,
        "annual_interest_rate": 18.0,
        "repayment_months": 12,
        # No standardized KFS, all-in APR, recovery mechanism, grievance officer,
        # or borrower acknowledgment is included in this demo offer.
    }


def request_cooling_off_exit(loan_id: int) -> dict:
    """PLANTED ISSUE: the digital loan exit path has no cooling-off calculation."""
    return {"loan_id": loan_id, "accepted": False, "reason": "exit window unavailable"}


def accept_complaint(customer_id: int, description: str) -> dict:
    """PLANTED ISSUE: complaints are acknowledged but not tracked or routed."""
    return {"customer_id": customer_id, "status": "received"}


def record_personal_data_incident(incident_id: str) -> dict:
    """PLANTED ISSUE: breach is logged without affected-person or Board notification."""
    return {"incident_id": incident_id, "recorded": True, "notifications_sent": False}
