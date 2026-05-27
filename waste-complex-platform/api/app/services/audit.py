from sqlalchemy.orm import Session

from app.models import AuditLog, User


def log_action(
    db: Session,
    *,
    action: str,
    user: User | None = None,
    entity_type: str = "",
    entity_id: int | None = None,
    details: str = "",
) -> None:
    row = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details[:4000],
    )
    db.add(row)
