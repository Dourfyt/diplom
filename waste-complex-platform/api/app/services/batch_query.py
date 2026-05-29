"""Фильтрация партий и расчёт просрочки хранения."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Query, Session

from app.models import WasteBatch


def apply_batch_filters(
    q: Query,
    *,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    source_department: str | None = None,
    hazard_class: int | None = None,
    overdue_storage: bool | None = None,
) -> Query:
    if status:
        q = q.filter(WasteBatch.status == status)
    if date_from:
        q = q.filter(WasteBatch.received_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(WasteBatch.received_at <= datetime.fromisoformat(date_to))
    if source_department:
        q = q.filter(WasteBatch.source_department == source_department)
    if hazard_class is not None:
        q = q.filter(WasteBatch.hazard_class == hazard_class)
    if overdue_storage:
        q = q.filter(
            text(
                "waste_batches.received_at + "
                "(waste_batches.storage_deadline_hours * interval '1 hour') < NOW()"
            )
        )
    return q


def is_storage_overdue(batch: WasteBatch, now: datetime | None = None) -> bool:
    now = now or datetime.utcnow()
    return now > batch.received_at + timedelta(hours=float(batch.storage_deadline_hours))


def count_dashboard_metrics(db: Session) -> dict[str, int]:
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    batches = db.query(WasteBatch).all()
    pending = sum(1 for b in batches if b.status == "accepted")
    rejected = sum(1 for b in batches if b.status == "rejected")
    today = sum(1 for b in batches if b.received_at >= today_start)
    overdue = sum(1 for b in batches if is_storage_overdue(b, now))
    return {
        "pending_classification_count": pending,
        "overdue_storage_count": overdue,
        "batches_today_count": today,
        "rejected_count": rejected,
    }
