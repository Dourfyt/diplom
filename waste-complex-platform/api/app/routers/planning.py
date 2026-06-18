"""API модуля планирования (совместим с planning-module)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, joinedload

from app.database import get_db
from app.labels import plan_status_ru
from app.models import User
from app.models import (
    Notification,
    NotificationStatus,
    PlanStatus,
    ProductionLine,
    ScheduleItem,
    SchedulePlan,
    WasteBatch,
)
from app.schemas import (
    BatchOut,
    BuildPlanRequest,
    DowntimeRequest,
    KpiDashboard,
    LineOut,
    NotificationOut,
    PlanActionResult,
    PlanOut,
    ScheduleItemOut,
    SimulationCompare,
    SimulationRequest,
)
from app.services.kpi import plan_kpi
from app.services.monitoring_sync import sync_stages_from_plan
from app.services.notifications import check_and_create_notifications
from app.services.plan_lifecycle import archive_other_approved, get_active_approved
from app.services.planner import (
    build_schedule,
    compute_priority,
    hours_until_deadline,
    replan_after_downtime,
)
from app.services.rbac import require_roles
from app.services.waste_balance import batch_balance

router = APIRouter(tags=["planning"])

PLANNING_VIEW = require_roles("operator", "chief", "ecologist", "admin")
PLANNING_WRITE = require_roles("chief", "admin")


def _status_code(plan: SchedulePlan) -> str:
    raw = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    return raw


def plan_to_out(plan: SchedulePlan) -> PlanOut:
    items = []
    for item in sorted(plan.items, key=lambda x: x.start_at):
        items.append(
            ScheduleItemOut(
                id=item.id,
                plan_id=item.plan_id,
                batch_id=item.batch_id,
                batch_code=item.batch.code,
                line_id=item.line_id,
                line_code=item.line.code,
                operation_code=item.operation_code,
                start_at=item.start_at,
                end_at=item.end_at,
                priority_score=item.priority_score,
                planned_output_tons=item.planned_output_tons,
                planned_loss_tons=item.planned_loss_tons,
            )
        )
    code = _status_code(plan)
    return PlanOut(
        id=plan.id,
        name=plan.name,
        horizon_hours=plan.horizon_hours,
        status=plan.status,
        status_label=plan_status_ru(code),
        version_no=getattr(plan, "version_no", 1) or 1,
        author=plan.author,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        is_simulation=plan.is_simulation,
        parent_plan_id=plan.parent_plan_id,
        items=items,
    )


def batch_to_out(b: WasteBatch, db: Session, now: datetime | None = None) -> BatchOut:
    now = now or datetime.utcnow()
    out = BatchOut.model_validate(b)
    out.priority_score = compute_priority(b, now)
    out.storage_risk_hours = hours_until_deadline(b, now)
    bal = batch_balance(db, b)
    out.processed_tons = bal["processed_tons"]
    out.disposed_tons = bal["disposed_tons"]
    out.remaining_tons = bal["remaining_tons"]
    out.organization_name = b.organization.name if b.organization else None
    return out


@router.get("/lines", response_model=list[LineOut])
def list_lines(db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    return db.query(ProductionLine).order_by(ProductionLine.code).all()


@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    now = datetime.utcnow()
    return [
        batch_to_out(b, db, now)
        for b in db.query(WasteBatch)
        .options(joinedload(WasteBatch.organization))
        .order_by(WasteBatch.code)
        .all()
    ]


@router.get("/plans", response_model=list[PlanOut])
def list_plans(view: str = "active", db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    q = db.query(SchedulePlan).options(
        joinedload(SchedulePlan.items).joinedload(ScheduleItem.batch),
        joinedload(SchedulePlan.items).joinedload(ScheduleItem.line),
    )
    if view == "active":
        all_plans = q.order_by(SchedulePlan.created_at.desc()).all()
        approved = get_active_approved(db)
        drafts = [
            p
            for p in all_plans
            if not p.is_simulation and _status_code(p) == PlanStatus.DRAFT.value
        ][:3]
        sims = [p for p in all_plans if p.is_simulation][:5]
        seen: set[int] = set()
        ordered: list[SchedulePlan] = []
        for p in [approved, *drafts, *sims]:
            if p and p.id not in seen:
                ordered.append(p)
                seen.add(p.id)
        return [plan_to_out(p) for p in ordered]
    plans = q.order_by(SchedulePlan.created_at.desc()).all()
    return [plan_to_out(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    plan = (
        db.query(SchedulePlan)
        .options(
            joinedload(SchedulePlan.items).joinedload(ScheduleItem.batch),
            joinedload(SchedulePlan.items).joinedload(ScheduleItem.line),
        )
        .filter(SchedulePlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(404, "План не найден")
    return plan_to_out(plan)


@router.post("/plans/build", response_model=PlanActionResult)
def build_plan(req: BuildPlanRequest, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    plan = build_schedule(
        db,
        name=req.name,
        horizon_hours=req.horizon_hours,
        batch_ids=req.batch_ids,
    )
    check_and_create_notifications(db, plan.id)
    loaded = get_plan(plan.id, db)
    return PlanActionResult(
        plan=loaded,
        message=f"Создан черновик версии {loaded.version_no}. Утвердите план для производства.",
    )


@router.post("/plans/{plan_id}/approve", response_model=PlanActionResult)
@router.post("/plans/{plan_id}/publish", response_model=PlanActionResult)
def approve_plan(plan_id: int, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    plan = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "План не найден")
    if plan.is_simulation:
        raise HTTPException(400, "Симуляцию нельзя утвердить")
    archived = archive_other_approved(db, plan_id)
    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.utcnow()
    db.commit()
    sync_stages_from_plan(db, plan_id)
    loaded = get_plan(plan_id, db)
    return PlanActionResult(
        plan=loaded,
        message=f"План v{loaded.version_no} утверждён. В архив: {archived}. Этапы мониторинга обновлены.",
    )


@router.post("/plans/{plan_id}/replan", response_model=PlanActionResult)
def replan(plan_id: int, req: DowntimeRequest, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    try:
        plan = replan_after_downtime(db, plan_id, req.line_code, req.duration_hours)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    check_and_create_notifications(db, plan.id)
    loaded = get_plan(plan.id, db)
    return PlanActionResult(plan=loaded, message=f"Черновик перепланирования v{loaded.version_no} создан.")


@router.post("/simulations", response_model=SimulationCompare)
def run_simulation(req: SimulationRequest, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    base = db.query(SchedulePlan).filter(SchedulePlan.id == req.base_plan_id).first()
    if not base:
        raise HTTPException(404, "Базовый план не найден")
    batch_ids = list({i.batch_id for i in base.items})
    downtime = req.line_downtime or {}
    if req.scenario == "accelerated":
        sim = build_schedule(
            db,
            name=f"{req.name} (ускоренный)",
            horizon_hours=round(base.horizon_hours * 0.85, 1),
            batch_ids=batch_ids,
            is_simulation=True,
            parent_plan_id=base.id,
        )
    elif req.scenario == "emergency":
        emergency_downtime = downtime or {"L2": 8.0}
        downtime_hours = max(emergency_downtime.values()) if emergency_downtime else 8.0
        sim = build_schedule(
            db,
            name=f"{req.name} (аварийный)",
            horizon_hours=min(base.horizon_hours + downtime_hours, 168.0),
            batch_ids=batch_ids,
            line_downtime_offsets=emergency_downtime,
            is_simulation=True,
            parent_plan_id=base.id,
        )
    else:
        sim = build_schedule(
            db,
            name=f"{req.name} (базовый)",
            horizon_hours=base.horizon_hours,
            batch_ids=batch_ids,
            is_simulation=True,
            parent_plan_id=base.id,
        )
    kpi_base = plan_kpi(db, base.id)
    kpi_sim = plan_kpi(db, sim.id)
    diff = {
        "idle_hours_delta": round(kpi_sim.total_idle_hours - kpi_base.total_idle_hours, 2),
        "storage_risk_delta": kpi_sim.batches_at_storage_risk - kpi_base.batches_at_storage_risk,
        "oee_delta": round(kpi_sim.oee_percent - kpi_base.oee_percent, 2),
    }
    return SimulationCompare(
        base_plan_id=base.id,
        sim_plan_id=sim.id,
        kpi_base=kpi_base,
        kpi_sim=kpi_sim,
        differences=diff,
    )


@router.get("/dashboard/kpi", response_model=KpiDashboard)
def dashboard(plan_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    if plan_id is None:
        active = get_active_approved(db)
        if active:
            plan_id = active.id
        else:
            latest = db.query(SchedulePlan).order_by(SchedulePlan.created_at.desc()).first()
            plan_id = latest.id if latest else None
    return plan_kpi(db, plan_id)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db), _: User = Depends(PLANNING_VIEW)):
    return db.query(Notification).order_by(Notification.created_at.desc()).limit(50).all()


@router.post("/notifications/check")
def trigger_notification_check(plan_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    created = check_and_create_notifications(db, plan_id)
    return {"created": len(created)}


@router.patch("/notifications/{nid}/ack")
def ack_notification(nid: int, db: Session = Depends(get_db), _: User = Depends(PLANNING_WRITE)):
    n = db.query(Notification).filter(Notification.id == nid).first()
    if not n:
        raise HTTPException(404, "Уведомление не найдено")
    n.status = NotificationStatus.ACKNOWLEDGED
    db.commit()
    return {"ok": True}
