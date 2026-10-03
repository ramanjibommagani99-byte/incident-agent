from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlmodel import Session, select

from .models import AuditLog


def _canonical(actor: str, action: str, payload: dict[str, Any], timestamp: str, prev_hash: str) -> bytes:
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    normalized_timestamp = parsed.astimezone(timezone.utc).isoformat()
    row = {"actor": actor, "action": action, "payload": payload, "timestamp": normalized_timestamp, "prev_hash": prev_hash}
    return json.dumps(row, sort_keys=True, separators=(",", ":"), default=str).encode()


def append_audit(session: Session, actor: str, action: str, payload: dict[str, Any]) -> AuditLog:
    last = session.exec(select(AuditLog).order_by(AuditLog.sequence.desc())).first()
    row = AuditLog(sequence=(last.sequence or 0) + 1 if last else 1, actor=actor, action=action, payload=payload, prev_hash=last.hash if last else "0" * 64, hash="")
    row.hash = hashlib.sha256(_canonical(actor, action, payload, row.timestamp.isoformat(), row.prev_hash)).hexdigest()
    session.add(row)
    session.flush()
    return row


def verify_chain(rows: list[AuditLog]) -> bool:
    previous = "0" * 64
    for row in rows:
        expected = hashlib.sha256(_canonical(row.actor, row.action, row.payload, row.timestamp.isoformat(), previous)).hexdigest()
        if row.prev_hash != previous or row.hash != expected:
            return False
        previous = row.hash
    return True
