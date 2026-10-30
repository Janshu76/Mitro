"""Synthetic ECL calculator for Mitro's DLG regression demo.

This deliberately simplified one-stage-at-a-time function is not an accounting
policy. It exists only to demonstrate a deterministic software regression case.
"""
from __future__ import annotations


def required_ecl(gross_ecl: float, dlg_cover: float, invoked_amount: float = 0.0) -> float:
    """Return required ECL after DLG cover (planted invocation-adjustment gap)."""
    if min(gross_ecl, dlg_cover, invoked_amount) < 0:
        raise ValueError("ECL, DLG cover, and invocation amount must be non-negative")
    # PLANTED ISSUE: the cover consumed by an invocation is not deducted here.
    available_cover = dlg_cover
    return max(gross_ecl - available_cover, 0.0)


def required_ecl_without_dlg(gross_ecl: float) -> float:
    """SECURE DECOY: portfolios without DLG retain the unadjusted gross ECL."""
    return max(gross_ecl, 0.0)
