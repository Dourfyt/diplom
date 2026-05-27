from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Notification, NotificationStatus, ScheduleItem, SchedulePlan, WasteBatch
from app.schemas import KpiDashboard
from app.services.planner import compute_priority, hours_until_deadline


def plan_kpi(db: Session, plan_id: int | None) -> KpiDashboard:
    now = datetime.utcnow()
    batches = db.query(WasteBatch).all()
    items: list[ScheduleItem] = []
    if plan_id:
        items = db.query(ScheduleItem).filter(ScheduleItem.plan_id == plan_id).all()

    scheduled_batch_ids = {i.batch_id for i in items}
    line_busy: dict[str, float] = {}
    line_total: dict[str, float] = {}

    for item in items:
        code = item.line.code
        dur = (item.end_at - item.start_at).total_seconds() / 3600
        line_busy[code] = line_busy.get(code, 0) + dur
        if plan_id:
            plan = db.get(SchedulePlan, plan_id)
            horizon = plan.horizon_hours if plan else 8
        else:
            horizon = 8
        line_total[code] = horizon

    utilization = {
        code: round(min(100.0, line_busy.get(code, 0) / max(line_total.get(code, 8), 0.01) * 100), 1)
        for code in set(line_total) | set(line_busy)
    }

    idle = sum(max(0, line_total.get(c, 8) - line_busy.get(c, 0)) for c in line_total)

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
        total_idle_hours=round(idle, 2),
        batches_at_storage_risk=at_risk,
        avg_priority=round(sum(priorities) / len(priorities), 2) if priorities else 0,
        notifications_new=notif_new,
        oee_percent=round(oee, 1),
        plan_completion_percent=round(
            len(scheduled_batch_ids) / max(len(batches), 1) * 100, 1
        ),
    )
