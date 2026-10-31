"""Append-only audit event helper for reviewer-visible workflow history."""
from datetime import datetime, timezone
from mitro.db import AuditEvent

def record_event(db, action: str, entity_type: str, entity_id: object = "", **details):
    event = AuditEvent(occurred_at=datetime.now(timezone.utc).isoformat(), action=action,
                       entity_type=entity_type, entity_id=str(entity_id or ""), details=details)
    db.add(event)
    return event
