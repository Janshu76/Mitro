"""Toy underwriting policy; not a credit model or lending recommendation."""
def score_application(amount: float, purpose: str) -> tuple[int, bool, str]:
    score = max(300, min(900, 780 - int(amount // 10_000)))
    approved = amount <= 500_000 and purpose.lower() not in {"speculation", "unknown"}
    return score, approved, "demo_policy_pass" if approved else "demo_policy_limit_or_purpose"
