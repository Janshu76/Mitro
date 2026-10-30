from difflib import SequenceMatcher
from sqlalchemy import select
from sqlalchemy.orm import Session
from mitro.db import DocumentVersion, Clause

def redline(db: Session, old_version_id: int, new_version_id: int) -> dict:
    old = db.get(DocumentVersion, old_version_id)
    new = db.get(DocumentVersion, new_version_id)
    if not old or not new:
        raise ValueError("Both version IDs must exist")
    if old.document_id != new.document_id:
        raise ValueError("Versions must belong to the same regulatory document")
    old_rows = db.scalars(select(Clause).where(Clause.version_id == old.id)).all()
    new_rows = db.scalars(select(Clause).where(Clause.version_id == new.id)).all()
    a = {c.citation: c.text for c in old_rows}
    b = {c.citation: c.text for c in new_rows}
    # First pair exact text that moved to a new citation (likely renumbering).
    old_by_text = {}
    new_by_text = {}
    for cite, text in a.items(): old_by_text.setdefault(text, []).append(cite)
    for cite, text in b.items(): new_by_text.setdefault(text, []).append(cite)
    moved_old, moved_new, changes = set(), set(), []
    for body, old_cites in old_by_text.items():
        for old_cite in old_cites:
            candidates = [c for c in new_by_text.get(body, []) if c != old_cite and c not in moved_new]
            if old_cite not in b and candidates:
                new_cite = candidates[0]
                moved_old.add(old_cite); moved_new.add(new_cite)
                changes.append({"citation": new_cite, "old_citation": old_cite, "change": "renumbered",
                                "old_text": body, "new_text": body, "similarity": 1.0})
    for key in sorted(set(a) | set(b)):
        if key in moved_old or key in moved_new: continue
        if key not in a: change = "added"
        elif key not in b: change = "removed"
        elif a[key] == b[key]: change = "unchanged"
        else: change = "modified"
        if change != "unchanged":
            changes.append({"citation": key, "change": change, "old_text": a.get(key), "new_text": b.get(key),
                            "similarity": round(SequenceMatcher(None, a.get(key, ""), b.get(key, "")).ratio(), 3)})
    return {"old_version": old.version_date, "new_version": new.version_date, "changes": changes,
            "note": "Conservative text comparison; exact moves are marked likely renumberings. Review against the source."}
