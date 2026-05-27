"""Движок планирования: приоритизация и жадное построение расписания."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    PlanStatus,
    ProductionLine,
    RoutingOperation,
    ScheduleItem,
    SchedulePlan,
    WasteBatch,
)
from app.services.plan_lifecycle import archive_open_drafts, next_version_no


def hours_until_deadline(batch: WasteBatch, now: datetime) -> float:
    elapsed = (now - batch.received_at).total_seconds() / 3600
    return max(0.0, batch.storage_deadline_hours - elapsed)


def compute_priority(batch: WasteBatch, now: datetime) -> float:
    """Взвешенная сумма: класс опасности, срочность хранения, экономика."""
    hazard = (6 - batch.hazard_class) * 25  # класс 3 важнее класса 5
    remaining = hours_until_deadline(batch, now)
    urgency = max(0.0, (48 - remaining) / 48) * 40
    economic = min(batch.economic_value / 1000, 1.0) * 15
    return round(hazard + urgency + economic, 2)


def parse_route(route_codes: str) -> list[str]:
    return [c.strip() for c in route_codes.replace("→", ",").split(",") if c.strip()]


def duration_hours(batch: WasteBatch, line: ProductionLine, op: RoutingOperation | None) -> float:
    base = op.base_duration_hours if op else 2.0
    load = batch.volume_tons / max(line.capacity_t_per_hour, 0.1)
    return max(base * 0.5, min(base * 2, load + base * 0.3))


def build_schedule(
    db: Session,
    name: str,
    horizon_hours: float,
    batch_ids: list[int] | None = None,
    line_availability: dict[str, bool] | None = None,
    line_downtime_offsets: dict[str, float] | None = None,
    is_simulation: bool = False,
    parent_plan_id: int | None = None,
) -> SchedulePlan:
    now = datetime.utcnow()
    lines = {ln.code: ln for ln in db.query(ProductionLine).all()}
    ops = {op.line_code: op for op in db.query(RoutingOperation).all()}

    q = db.query(WasteBatch).filter(WasteBatch.status.in_(["accepted", "queued"]))
    if batch_ids:
        q = q.filter(WasteBatch.id.in_(batch_ids))
    batches = q.all()

    scored = sorted(
        batches,
        key=lambda b: compute_priority(b, now),
        reverse=True,
    )

    version_no = 1 if is_simulation else next_version_no(db)
    if not is_simulation:
        archive_open_drafts(db)

    plan = SchedulePlan(
        name=name,
        horizon_hours=horizon_hours,
        status=PlanStatus.DRAFT,
        version_no=version_no,
        is_simulation=is_simulation,
        parent_plan_id=parent_plan_id,
    )
    db.add(plan)
    db.flush()

    line_free_at: dict[str, datetime] = {code: now for code in lines}
    if line_downtime_offsets:
        for code, hours in line_downtime_offsets.items():
            if code in line_free_at:
                line_free_at[code] = now + timedelta(hours=hours)

    horizon_end = now + timedelta(hours=horizon_hours)

    for batch in scored:
        route = parse_route(batch.route_codes)
        priority = compute_priority(batch, now)

        for line_code in route:
            if line_code not in lines:
                continue
            line = lines[line_code]
            if line_availability and not line_availability.get(line_code, True):
                continue
            if not line.is_available:
                continue

            op = ops.get(line_code)
            dur = timedelta(hours=duration_hours(batch, line, op))
            start = max(line_free_at[line_code], now)
            end = start + dur

            if start >= horizon_end:
                continue

            output = batch.volume_tons * (op.output_ratio if op else 0.85)
            loss = batch.volume_tons * (op.loss_ratio if op else 0.15)

            item = ScheduleItem(
                plan_id=plan.id,
                batch_id=batch.id,
                line_id=line.id,
                operation_code=op.code if op else f"OP_{line_code}",
                start_at=start,
                end_at=end,
                priority_score=priority,
                planned_output_tons=round(output, 2),
                planned_loss_tons=round(loss, 2),
            )
            db.add(item)
            line_free_at[line_code] = end

    db.commit()
    db.refresh(plan)
    return plan


def replan_after_downtime(
    db: Session,
    plan_id: int,
    line_code: str,
    downtime_hours: float,
) -> SchedulePlan:
    old = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not old:
        raise ValueError("Plan not found")

    batch_ids = list({item.batch_id for item in old.items})
    plan = build_schedule(
        db,
        name=f"Перепланирование после простоя {line_code} (вер. {old.version_no})",
        horizon_hours=old.horizon_hours,
        batch_ids=batch_ids,
        line_downtime_offsets={line_code: downtime_hours},
        is_simulation=False,
        parent_plan_id=old.id,
    )
    return plan
