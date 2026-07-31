from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record_event(
    db: Session,
    *,
    account_id: int,
    action: str,
    target_email: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        account_id=account_id,
        action=action,
        target_email=target_email,
        details=details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_recent_events(
    db: Session,
    account_id: int,
    *,
    limit: int = 20,
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.account_id == account_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def serialize_event(event: AuditLog) -> dict[str, Any]:
    return {
        "id": event.id,
        "action": event.action,
        "target_email": event.target_email,
        "details": event.details,
        "created_at": event.created_at.isoformat(),
    }
