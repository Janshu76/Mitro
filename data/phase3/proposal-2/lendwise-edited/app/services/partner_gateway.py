"""Local fake partner gateway. It never transmits customer data or money."""
def send_disbursement(partner: str, loan_id: int, amount: float) -> dict:
    return {"accepted": True, "receipt_id": f"SIM-{partner[:8].upper()}-{loan_id:06d}"}
