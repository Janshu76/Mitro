"""Narrow, deterministic patch templates for the synthetic Lendwise target.

The first release intentionally supports only two exact demo cases. It never
executes arbitrary uploaded repositories and never writes into the source tree.
"""
from __future__ import annotations

import difflib
from pathlib import Path

from mitro.database import ROOT

LENDWISE = ROOT / "targets" / "lendwise"

DLG_BEFORE = '''    # PLANTED ISSUE: the cover consumed by an invocation is not deducted here.
    available_cover = dlg_cover
'''
DLG_AFTER = '''    # Apply the invocation before calculating ECL against the remaining cover.
    available_cover = max(dlg_cover - invoked_amount, 0.0)
'''
CONSENT_SCHEMA_BEFORE = '''class LegacyImportIn(BaseModel):
    full_name: str
    phone: str
    pan_last4: str
    requested_amount: float
    purpose: str
    # Planted scenario: this legacy intake schema has no consent field.
'''
CONSENT_SCHEMA_AFTER = '''class LegacyImportIn(BaseModel):
    full_name: str
    phone: str
    pan_last4: str
    requested_amount: float
    purpose: str
    consent: bool
'''
CONSENT_ROUTE_BEFORE = '''def import_legacy_application(body: LegacyImportIn, db: Session = Depends(get_db)):
    # PLANTED ISSUE: this alternate path creates a customer record without consent capture/validation.
    customer = Customer'''
CONSENT_ROUTE_AFTER = '''def import_legacy_application(body: LegacyImportIn, db: Session = Depends(get_db)):
    if not body.consent:
        raise HTTPException(400, "Customer consent is required for this import")
    customer = Customer'''

def _diff(path: str, before: str, after: str) -> str:
    return "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}"))

def _test_file(kind: str) -> str:
    if kind == "dlg_invocation_recompute":
        return '''import unittest
from app.services.provisioning import required_ecl, required_ecl_without_dlg

class DlgInvocationRegression(unittest.TestCase):
    def test_invocation_reduces_cover_before_recomputing_ecl(self):
        self.assertEqual(required_ecl(5000.0, 4000.0, 2000.0), 3000.0)

    def test_recompute_clamps_remaining_cover_at_zero(self):
        self.assertEqual(required_ecl(5000.0, 1000.0, 2000.0), 5000.0)

    def test_no_dlg_decoy_keeps_gross_ecl(self):
        self.assertEqual(required_ecl_without_dlg(5000.0), 5000.0)

if __name__ == "__main__":
    unittest.main()
'''
    return '''import unittest
from fastapi import HTTPException
from app.routers.applications import import_legacy_application
from app.schemas import LegacyImportIn

class ConsentRegression(unittest.TestCase):
    def test_missing_consent_is_rejected_before_customer_write(self):
        body = LegacyImportIn(full_name="Demo Borrower", phone="9999999999", pan_last4="1234",
            requested_amount=10000, purpose="education", consent=False)
        with self.assertRaises(HTTPException) as raised:
            import_legacy_application(body, db=object())
        self.assertEqual(raised.exception.status_code, 400)

if __name__ == "__main__":
    unittest.main()
'''

def build_change(clause_text: str, citation: str) -> dict:
    """Create an exact-quote-grounded, supported demo change or explain limitation."""
    text = clause_text.lower()
    if "dlg" in text and any(term in text for term in ("invocation", "recompute", "reduced dlg cover")):
        scenario = "dlg_invocation_recompute"
        edits = [{"file": "app/services/provisioning.py", "before": DLG_BEFORE, "after": DLG_AFTER}]
        title = "Recompute ECL using the reduced DLG cover"
        expected = "After a DLG invocation, remaining cover equals max(original cover minus the invocation, zero); the ECL calculation uses that remaining cover."
        rationale = "The selected clause says an invocation reduces DLG cover and ECL provisioning must be recomputed using the reduced cover. Lendwise's demo helper currently subtracts the original cover."
    elif "consent" in text and any(term in text for term in ("prior", "explicit", "audit trail", "need-based", "collection")):
        scenario = "legacy_import_consent"
        edits = [
            {"file": "app/schemas.py", "before": CONSENT_SCHEMA_BEFORE, "after": CONSENT_SCHEMA_AFTER},
            {"file": "app/routers/applications.py", "before": CONSENT_ROUTE_BEFORE, "after": CONSENT_ROUTE_AFTER},
        ]
        title = "Require consent on the legacy import path"
        expected = "The legacy import endpoint rejects a request without affirmative consent before creating a customer record."
        rationale = "The selected clause refers to prior and explicit consent. Lendwise's primary intake checks consent, but its legacy import path does not. This demo patch addresses only that route."
    else:
        raise ValueError("No safe Lendwise patch template matches this clause yet. Mitro can still show Phase 2 code locations; no code was changed.")

    diffs = []
    for edit in edits:
        source = (LENDWISE / edit["file"]).read_text(encoding="utf-8")
        if source.count(edit["before"]) != 1:
            raise ValueError(f"The expected demo code pattern in {edit['file']} changed; refusing to create a patch.")
        diffs.append(_diff(edit["file"], edit["before"], edit["after"]))
    return {"scenario": scenario, "title": title, "expected_behavior": expected,
            "rationale": rationale, "citation": citation, "edits": edits,
            "diff": "\n".join(diffs), "test_filename": "test_mitro_phase3_generated.py",
            "test_source": _test_file(scenario),
            "method": "deterministic Lendwise demo template",
            "limitations": ["Demo template is selected from clause wording and must be reviewed.",
                            "This is not a legal applicability decision or accounting interpretation.",
                            "Automatic patching is limited to the included Lendwise demo target."]}

