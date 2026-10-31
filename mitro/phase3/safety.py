"""Deterministic scope and content checks for proposed demo patches."""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from pathlib import PurePosixPath

ALLOWED_FILES = {
    "dlg_invocation_recompute": {"app/services/provisioning.py"},
    "legacy_import_consent": {"app/schemas.py", "app/routers/applications.py"},
}
PROTECTED_PARTS = {".env", "settings.py", "config.py", "database.py", "migrations", "alembic", "payments.py", "auth.py"}
SECRET_RE = re.compile(r"(?i)(api[_-]?key|secret|password|bearer\s+)[=: ]+[^\s\"']{8,}")

def evaluate_patch_safety(scenario: str, edits: list[dict]) -> dict:
    allowed = ALLOWED_FILES.get(scenario)
    if allowed is None:
        return {"allowed": False, "risk": "blocked", "reasons": ["Unknown patch scenario"], "files": [], "changed_lines": 0}
    files, changed, reasons = [], 0, []
    for edit in edits:
        raw = str(edit.get("file", ""))
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts or "\\" in raw:
            reasons.append(f"Unsafe path rejected: {raw}")
            continue
        normalized = path.as_posix()
        files.append(normalized)
        if normalized not in allowed:
            reasons.append(f"File is outside the approved scenario allowlist: {normalized}")
        if any(part.lower() in PROTECTED_PARTS for part in path.parts):
            reasons.append(f"Protected file requires separate approval: {normalized}")
        before, after = str(edit.get("before", "")), str(edit.get("after", ""))
        before_lines, after_lines = before.splitlines(), after.splitlines()
        changed += sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in
                       SequenceMatcher(a=before_lines, b=after_lines, autojunk=False).get_opcodes()
                       if tag != "equal")
        if SECRET_RE.search(after):
            reasons.append(f"Potential secret material detected in proposed content: {normalized}")
    if len(files) > 5:
        reasons.append("Patch exceeds the 5-file change limit")
    if changed > 100:
        reasons.append("Patch exceeds the 100-line change limit")
    if not edits:
        reasons.append("Patch has no validated edits")
    sensitive = any(re.search(r"(?i)(auth|payment|credential|migration|secret)", p) for p in files)
    risk = "high" if sensitive or len(files) > 2 or changed > 40 else "medium" if changed > 15 else "low"
    return {"allowed": not reasons, "risk": risk if not reasons else "blocked", "reasons": reasons,
            "files": files, "changed_lines": changed, "approval_required": True,
            "execution_boundary": "separate synthetic Lendwise copy only"}
