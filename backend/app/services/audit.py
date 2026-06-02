"""Audit logging helper."""
import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    company_id: str | None,
    user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: Any = None,
    after: Any = None,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            company_id=company_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=json.dumps(before, default=str) if before is not None else None,
            after_json=json.dumps(after, default=str) if after is not None else None,
            ip=ip,
        )
    )
