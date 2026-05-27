"""Синхронизация этапов мониторинга с партией и утверждённым планом."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.labels import STAGE_STATUS_RU
from app.models import BatchStageProgress, ProcessingStage, ScheduleItem, SchedulePlan, WasteBatch


def ensure_batch_stages(db: Session, batch_id: int) -> None:
    stages = db.query(ProcessingStage).order_by(ProcessingStage.sequence_order).all()
    existing = {
        p.stage_id
        for p in db.query(BatchStageProgress).filter(BatchStageProgress.batch_id == batch_id).all()
    }
    for stage in stages:
        if stage.id in existing:
            continue
        db.add(
            BatchStageProgress(
                batch_id=batch_id,
                stage_id=stage.id,
                status="pending",
            )
        )
    db.commit()


def sync_stages_from_plan(db: Session, plan_id: int) -> None:
    plan = db.query(SchedulePlan).filter(SchedulePlan.id == plan_id).first()
    if not plan:
        return
    items = (
        db.query(ScheduleItem)
        .filter(ScheduleItem.plan_id == plan_id)
        .order_by(ScheduleItem.start_at)
        .all()
    )
    stage_by_line = {
        s.line_code: s
        for s in db.query(ProcessingStage).all()
        if s.line_code
    }
    for item in items:
        ensure_batch_stages(db, item.batch_id)
        stage = stage_by_line.get(item.line.code)
        if not stage:
            continue
        prog = (
            db.query(BatchStageProgress)
            .filter(
                BatchStageProgress.batch_id == item.batch_id,
                BatchStageProgress.stage_id == stage.id,
            )
            .first()
        )
        if not prog:
            continue
        prog.planned_start = item.start_at
        prog.planned_end = item.end_at
        if prog.status == "pending":
            prog.status = "in_progress" if item.start_at <= datetime.utcnow() else "pending"
    db.commit()


def progress_to_dict(prog: BatchStageProgress, batch: WasteBatch) -> dict:
    return {
        "id": prog.id,
        "batch_id": prog.batch_id,
        "batch_code": batch.code,
        "stage_id": prog.stage_id,
        "stage_code": prog.stage.code,
        "stage_name": prog.stage.name,
        "status": prog.status,
        "status_label": STAGE_STATUS_RU.get(prog.status, prog.status),
        "planned_start": prog.planned_start,
        "planned_end": prog.planned_end,
        "actual_start": prog.actual_start,
        "actual_end": prog.actual_end,
        "deviation_percent": prog.deviation_percent,
    }
