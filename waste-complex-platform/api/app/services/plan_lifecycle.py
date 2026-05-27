"""Жизненный цикл версий плана — как в дипломе: черновик → утверждение → архив."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import PlanStatus, SchedulePlan


def next_version_no(db: Session) -> int:
    current = (
        db.query(func.max(SchedulePlan.version_no))
        .filter(SchedulePlan.is_simulation.is_(False))
        .scalar()
    )
    return (current or 0) + 1


def archive_other_approved(db: Session, except_plan_id: int) -> int:
    """При утверждении новой версии старые утверждённые уходят в архив."""
    q = (
        db.query(SchedulePlan)
        .filter(
            SchedulePlan.is_simulation.is_(False),
            SchedulePlan.id != except_plan_id,
            SchedulePlan.status == PlanStatus.APPROVED,
        )
    )
    count = 0
    for plan in q.all():
        plan.status = PlanStatus.ARCHIVED
        count += 1
    return count


def archive_open_drafts(db: Session, except_plan_id: int | None = None) -> int:
    """Оставляем один актуальный черновик — предыдущие черновики в архив."""
    q = db.query(SchedulePlan).filter(
        SchedulePlan.is_simulation.is_(False),
        SchedulePlan.status == PlanStatus.DRAFT,
    )
    if except_plan_id:
        q = q.filter(SchedulePlan.id != except_plan_id)
    count = 0
    for plan in q.all():
        plan.status = PlanStatus.ARCHIVED
        count += 1
    return count


def get_active_approved(db: Session) -> SchedulePlan | None:
    return (
        db.query(SchedulePlan)
        .filter(
            SchedulePlan.is_simulation.is_(False),
            SchedulePlan.status == PlanStatus.APPROVED,
        )
        .order_by(SchedulePlan.approved_at.desc().nullslast(), SchedulePlan.id.desc())
        .first()
    )
