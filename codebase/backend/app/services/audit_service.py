"""
audit_service.py — append-only, hash-chained audit recorder.

record(...)        appends one event, chaining this_hash to the previous event's hash.
verify_chain()     recomputes the whole chain and reports the first break (if any).

CONCURRENCY: chain appends are serialized with pg_advisory_xact_lock so multiple Gunicorn
workers/hosts cannot fork the chain. A Python threading.Lock is NOT sufficient.

STORES: rows in audit_events (append-only; migration REVOKEs UPDATE/DELETE from app user).
Full design: ../../feature_plans/audit_trail_plan.md
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import text

from app.extensions import db
from app.models.audit_event import AuditEvent

AUDIT_CHAIN_LOCK_KEY = 741_852_963   # fixed advisory-lock id for the audit chain


class AuditService:
    def record(self, event_type: str, actor_user_id=None, target_type=None,
               target_id=None, case_id=None, ip_address=None, metadata=None) -> AuditEvent:
        """Append one audit event. Serialized cross-process via advisory lock.
        RETURNS: the persisted AuditEvent. Never raises for 'normal' inputs."""
        db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUDIT_CHAIN_LOCK_KEY})

        last = db.session.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        prev_hash = last.this_hash if last else "0" * 64
        now = datetime.now(timezone.utc)

        event = AuditEvent(
            event_type=event_type, actor_user_id=actor_user_id, target_type=target_type,
            target_id=str(target_id) if target_id else None,
            case_id=str(case_id) if case_id else None,
            ip_address=ip_address, event_metadata=metadata or {},
            prev_hash=prev_hash, created_at=now, this_hash="",
        )
        event.this_hash = self._compute_hash(prev_hash, event)
        db.session.add(event)
        db.session.commit()   # releases the advisory lock
        return event

    def _compute_hash(self, prev_hash: str, event: AuditEvent) -> str:
        payload = "|".join([
            prev_hash, event.event_type,
            str(event.actor_user_id or ""), str(event.target_type or ""),
            str(event.target_id or ""), str(event.case_id or ""),
            str(event.ip_address or ""), event.created_at.isoformat(),
            json.dumps(event.event_metadata or {}, sort_keys=True, separators=(",", ":")),
        ])
        return hashlib.sha256(payload.encode()).hexdigest()

    def verify_chain(self) -> dict:
        """Recompute the audit chain and report the first broken event, if any."""
        events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()

        expected_prev = "0" * 64
        first_break = None

        for event in events:
            if event.prev_hash != expected_prev:
               first_break = event.id
               break

            if self._compute_hash(event.prev_hash, event) != event.this_hash:
               first_break = event.id
               break

            expected_prev = event.this_hash

        return {
            "total_events": len(events),
            "chain_valid": first_break is None,
            "first_break_at": first_break,
    }


audit_service = AuditService()   # import this singleton everywhere
