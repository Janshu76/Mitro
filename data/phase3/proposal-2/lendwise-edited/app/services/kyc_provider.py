"""Synthetic third-party KYC connector used only to plant an integration weakness.
The default hostname is reserved and will not resolve. No real provider is configured.
"""
import os
import httpx

PROVIDER_URL = os.getenv("KYC_PROVIDER_URL", "https://kyc.example.invalid/verify")

def verify_identity(full_name: str, pan_last4: str) -> dict:
    # PLANTED ISSUE: TLS certificate verification is disabled; don't point this at a real provider.
    # PLANTED ISSUE: request/response access is not recorded in a vendor audit trail.
    with httpx.Client(verify=False, timeout=2.0) as client:
        response = client.post(PROVIDER_URL, json={"name": full_name, "pan_last4": pan_last4})
        response.raise_for_status()
        body = response.json()
    return {"verified": bool(body.get("verified")), "status": str(body.get("status", "unknown"))}
