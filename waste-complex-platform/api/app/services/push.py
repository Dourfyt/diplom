"""FCM push-уведомления через Firebase Admin SDK (опционально)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, UserDevice

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_checked = False


def _ensure_firebase():
    global _firebase_app, _firebase_checked
    if _firebase_checked:
        return _firebase_app
    _firebase_checked = True
    cred_path = settings.firebase_credentials_path.strip()
    if not cred_path:
        logger.info("FCM: FIREBASE_CREDENTIALS_PATH не задан — push отключён")
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            _firebase_app = firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            _firebase_app = firebase_admin.get_app()
        logger.info("FCM: Firebase Admin SDK инициализирован")
        return _firebase_app
    except Exception as exc:
        logger.warning("FCM: не удалось инициализировать Firebase: %s", exc)
        return None


def _tokens_for_roles(db: Session, roles: tuple[str, ...]) -> list[str]:
    rows = (
        db.query(UserDevice.fcm_token)
        .join(User, UserDevice.user_id == User.id)
        .filter(User.is_active.is_(True), User.role.in_(roles))
        .all()
    )
    return [r[0] for r in rows if r[0]]


def send_push(
    db: Session,
    *,
    title: str,
    body: str,
    roles: tuple[str, ...] = ("chief", "ecologist", "admin"),
    data: dict[str, str] | None = None,
) -> int:
    """Отправить push пользователям с указанными ролями. Возвращает число успешных отправок."""
    if _ensure_firebase() is None:
        return 0

    tokens = _tokens_for_roles(db, roles)
    if not tokens:
        return 0

    from firebase_admin import messaging

    payload_data: dict[str, str] = {k: str(v) for k, v in (data or {}).items()}
    sent = 0
    for token in tokens:
        try:
            messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=payload_data,
                    token=token,
                )
            )
            sent += 1
        except Exception as exc:
            logger.warning("FCM: ошибка отправки на %s…: %s", token[:12], exc)
    return sent


def notify_new_deviation(
    db: Session,
    *,
    batch_code: str,
    deviation_type: str,
    batch_id: int,
    deviation_id: int,
) -> None:
    send_push(
        db,
        title=f"Новое отклонение: {batch_code}",
        body=f"Тип: {deviation_type}",
        data={
            "type": "deviation_created",
            "batch_id": str(batch_id),
            "deviation_id": str(deviation_id),
        },
    )


def notify_emergency_stop(
    db: Session,
    *,
    batch_code: str,
    batch_id: int,
    comment: str,
) -> None:
    send_push(
        db,
        title=f"Аварийная остановка: {batch_code}",
        body=comment[:200] or "Аварийная остановка партии",
        roles=("chief", "ecologist", "admin", "operator"),
        data={"type": "emergency_stop", "batch_id": str(batch_id)},
    )


def notify_planning_alert(
    db: Session,
    *,
    title: str,
    message: str,
    batch_id: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    data: dict[str, str] = {"type": "planning_alert"}
    if batch_id is not None:
        data["batch_id"] = str(batch_id)
    if extra:
        data.update({k: str(v) for k, v in extra.items()})
    send_push(db, title=title, body=message[:200], data=data)
