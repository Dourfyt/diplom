from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Notification, NotificationStatus, ScheduleItem, SchedulePlan, WasteBatch
from app.schemas import KpiDashboard
from app.services.planner import compute_priority, hours_until_deadline


def _line_idle_hours(
    items_on_line: list[ScheduleItem],
    window_start: datetime,
    window_end: datetime,
) -> float:
    """Простой по разрывам в окне плана (в т.ч. вынужденный до первой операции)."""
    if window_end <= window_start:
        return 0.0
    if not items_on_line:
        return (window_end - window_start).total_seconds() / 3600

    sorted_items = sorted(items_on_line, key=lambda x: x.start_at)
    idle_seconds = 0.0
    idle_seconds += max(0.0, (sorted_items[0].start_at - window_start).total_seconds())
    for i in range(len(sorted_items) - 1):
        idle_seconds += max(
            0.0,
            (sorted_items[i + 1].start_at - sorted_items[i].end_at).total_seconds(),
        )
    idle_seconds += max(0.0, (window_end - sorted_items[-1].end_at).total_seconds())
    return idle_seconds / 3600


def plan_kpi(db: Session, plan_id: int | None) -> KpiDashboard:
    now = datetime.utcnow()
    batches = db.query(WasteBatch).all()
    items: list[ScheduleItem] = []
    plan: SchedulePlan | None = None
    if plan_id:
        plan = db.get(SchedulePlan, plan_id)
        items = db.query(ScheduleItem).filter(ScheduleItem.plan_id == plan_id).all()

    scheduled_batch_ids = {i.batch_id for i in items}
    horizon = plan.horizon_hours if plan else 8.0
    window_start = plan.created_at if plan else now
    window_end = window_start + timedelta(hours=horizon)

    by_line: dict[str, list[ScheduleItem]] = {}
    line_busy: dict[str, float] = {}
    for item in items:
        code = item.line.code
        by_line.setdefault(code, []).append(item)
        dur = (item.end_at - item.start_at).total_seconds() / 3600
        line_busy[code] = line_busy.get(code, 0) + dur

    idle = round(
        sum(_line_idle_hours(line_items, window_start, window_end) for line_items in by_line.values()),
        2,
    )

    utilization = {
        code: round(min(100.0, line_busy.get(code, 0) / max(horizon, 0.01) * 100), 1)
        for code in by_line
    }

    at_risk = 0
    priorities = []
    for b in batches:
        if b.id not in scheduled_batch_ids:
            rem = hours_until_deadline(b, now)
            if rem < 6:
                at_risk += 1
        priorities.append(compute_priority(b, now))

    notif_new = (
        db.query(Notification)
        .filter(Notification.status == NotificationStatus.NEW)
        .count()
    )

    oee = sum(utilization.values()) / len(utilization) if utilization else 0.0

    return KpiDashboard(
        plan_id=plan_id,
        total_batches=len(batches),
        scheduled_batches=len(scheduled_batch_ids),
        line_utilization=utilization,
        total_idle_hours=idle,
        batches_at_storage_risk=at_risk,
        avg_priority=round(sum(priorities) / len(priorities), 2) if priorities else 0,
        notifications_new=notif_new,
        oee_percent=round(oee, 1),
        plan_completion_percent=round(
            len(scheduled_batch_ids) / max(len(batches), 1) * 100, 1
        ),
    )
