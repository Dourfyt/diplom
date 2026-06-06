"""API модуля мониторинга этапов (Хука М.М.)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BatchStageProgress, ScheduleItem, StageEvent, WasteBatch
from app.services.plan_lifecycle import get_active_approved
from app.services.waste_balance import record_operation
from app.schemas import (
    MonitoringBatchOut,
    StageEventCreate,
    StageOut,
    StageProgressOut,
    StageStatusUpdate,
)
from app.services.monitoring_sync import ensure_batch_stages, progress_to_dict
from app.services.planner import compute_priority, hours_until_deadline
from app.services.push import notify_emergency_stop
from app.services.ws_hub import schedule_batch_updated
from app.schemas import BatchBalanceOut, BatchOut
from app.services.waste_balance import batch_balance

router = APIRouter(tags=["monitoring"])


@router.get("/stages", response_model=list[StageOut])
def list_stages(db: Session = Depends(get_db)):
    from app.models import ProcessingStage

    return db.query(ProcessingStage).order_by(ProcessingStage.sequence_order).all()


@router.get("/batches", response_model=list[MonitoringBatchOut])
def list_batches_monitoring(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    result = []
    for batch in db.query(WasteBatch).order_by(WasteBatch.code).all():
        ensure_batch_stages(db, batch.id)
        rows = (
            db.query(BatchStageProgress)
            .options(joinedload(BatchStageProgress.stage))
            .filter(BatchStageProgress.batch_id == batch.id)
            .all()
        )
        stages = [StageProgressOut(**progress_to_dict(r, batch)) for r in rows]
        b = BatchOut.model_validate(batch)
        b.priority_score = compute_priority(batch, now)
        b.storage_risk_hours = hours_until_deadline(batch, now)
        result.append(MonitoringBatchOut(batch=b, stages=stages))
    return result


@router.get("/batches/{batch_id}", response_model=MonitoringBatchOut)
def get_batch_monitoring(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    ensure_batch_stages(db, batch.id)
    rows = (
        db.query(BatchStageProgress)
        .options(joinedload(BatchStageProgress.stage))
        .filter(BatchStageProgress.batch_id == batch_id)
        .all()
    )
    now = datetime.utcnow()
    b = BatchOut.model_validate(batch)
    b.priority_score = compute_priority(batch, now)
    b.storage_risk_hours = hours_until_deadline(batch, now)
    return MonitoringBatchOut(
        batch=b,
        stages=[StageProgressOut(**progress_to_dict(r, batch)) for r in rows],
    )


@router.get("/batches/qr/{token}", response_model=MonitoringBatchOut)
def get_by_qr(token: str, db: Session = Depends(get_db)):
    batch = db.query(WasteBatch).filter(WasteBatch.qr_token == token).first()
    if not batch:
        raise HTTPException(404, "Партия по QR не найдена")
    return get_batch_monitoring(batch.id, db)


@router.get("/batches/{batch_id}/balance", response_model=BatchBalanceOut)
def get_batch_balance_monitoring(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    return BatchBalanceOut(**batch_balance(db, batch))


def _processing_qty_for_stage(
    db: Session, batch_id: int, line_code: str, explicit: float | None
) -> float | None:
    if explicit is not None:
        return explicit
    from app.models import ProductionLine

    plan = get_active_approved(db)
    if not plan:
        return None
    item = (
        db.query(ScheduleItem)
        .join(ProductionLine, ScheduleItem.line_id == ProductionLine.id)
        .filter(
            ScheduleItem.plan_id == plan.id,
            ScheduleItem.batch_id == batch_id,
            ProductionLine.code == line_code,
        )
        .order_by(ScheduleItem.end_at.desc())
        .first()
    )
    if item and item.planned_output_tons > 0:
        return item.planned_output_tons
    return None


@router.patch("/batches/{batch_id}/stages/{stage_id}", response_model=StageProgressOut)
def update_stage_status(
    batch_id: int,
    stage_id: int,
    body: StageStatusUpdate,
    db: Session = Depends(get_db),
):
    prog = (
        db.query(BatchStageProgress)
        .options(joinedload(BatchStageProgress.stage))
        .filter(
            BatchStageProgress.batch_id == batch_id,
            BatchStageProgress.stage_id == stage_id,
        )
        .first()
    )
    if not prog:
        raise HTTPException(404, "Этап партии не найден")
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    stage_code = prog.stage.code if prog.stage else ""
    now = datetime.utcnow()
    prog.status = body.status
    if body.status == "in_progress" and not prog.actual_start:
        prog.actual_start = now
    if body.status == "done":
        prog.actual_end = now
        if prog.planned_end and prog.actual_end:
            planned_h = (prog.planned_end - (prog.planned_start or prog.planned_end)).total_seconds() / 3600
            actual_h = (prog.actual_end - (prog.actual_start or prog.actual_end)).total_seconds() / 3600
            if planned_h > 0:
                prog.deviation_percent = round((actual_h - planned_h) / planned_h * 100, 1)
        if body.record_processing and batch:
            line_code = prog.stage.line_code if prog.stage else ""
            qty = _processing_qty_for_stage(db, batch_id, line_code, body.quantity_tons)
            if qty:
                try:
                    record_operation(
                        db,
                        batch_id=batch_id,
                        operation_type="processing",
                        quantity_tons=qty,
                        notes=f"Этап {stage_code} завершён (мониторинг)",
                    )
                except ValueError as e:
                    raise HTTPException(400, str(e)) from e
    db.commit()
    db.refresh(prog)
    schedule_batch_updated(batch_id)
    return StageProgressOut(**progress_to_dict(prog, batch))


@router.post("/batches/{batch_id}/stages/{stage_id}/events")
def add_stage_event(
    batch_id: int,
    stage_id: int,
    body: StageEventCreate,
    db: Session = Depends(get_db),
):
    prog = (
        db.query(BatchStageProgress)
        .filter(
            BatchStageProgress.batch_id == batch_id,
            BatchStageProgress.stage_id == stage_id,
        )
        .first()
    )
    if not prog:
        raise HTTPException(404, "Этап не найден")
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    ev = StageEvent(
        progress_id=prog.id,
        event_type=body.event_type,
        comment=body.comment,
        operator_name=body.operator_name,
    )
    db.add(ev)
    db.commit()
    if body.event_type == "emergency_stop" and batch:
        notify_emergency_stop(
            db,
            batch_code=batch.code,
            batch_id=batch_id,
            comment=body.comment,
        )
        schedule_batch_updated(batch_id)
    return {"id": ev.id, "created_at": ev.created_at}
