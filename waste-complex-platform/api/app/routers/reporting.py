"""API модуля отчётности и экологического контроля (Журавлёва М.Е.)."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EnvironmentalMeasurement, Organization, User, WasteBatch, WasteOperation
from app.schemas import BatchBalanceOut, MeasurementCreate, MeasurementOut, ReportingDashboard, WasteOperationOut
from app.services.kpi import plan_kpi
from app.services.plan_lifecycle import get_active_approved
from app.services.rbac import require_roles
from app.services.waste_balance import batch_balance

router = APIRouter(tags=["reporting"])


def _op_out(op: WasteOperation) -> WasteOperationOut:
    return WasteOperationOut(
        id=op.id,
        organization_id=op.organization_id,
        waste_type_id=op.waste_type_id,
        batch_id=op.batch_id,
        operation_type=op.operation_type,
        quantity_tons=op.quantity_tons,
        user_id=op.user_id,
        user_name=op.user.full_name if op.user else None,
        old_hazard_class=op.old_hazard_class,
        new_hazard_class=op.new_hazard_class,
        operation_at=op.operation_at,
        notes=op.notes,
    )


@router.get("/dashboard", response_model=ReportingDashboard)
def reporting_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    org = db.query(Organization).first()
    batches = db.query(WasteBatch).all()
    processed_batches = sum(1 for b in batches if b.status in ("processing", "done"))
    total_vol = sum(b.volume_tons for b in batches)
    total_processed = 0.0
    total_disposed = 0.0
    total_remaining = 0.0
    for b in batches:
        bal = batch_balance(db, b)
        total_processed += bal["processed_tons"]
        total_disposed += bal["disposed_tons"]
        total_remaining += bal["remaining_tons"]
    avg_hazard = sum(b.hazard_class for b in batches) / max(len(batches), 1)
    active = get_active_approved(db)
    kpi = plan_kpi(db, active.id if active else None)
    return ReportingDashboard(
        organization_name=org.name if org else "—",
        total_batches=len(batches),
        batches_processed=processed_batches,
        total_volume_tons=round(total_vol, 2),
        total_processed_tons=round(total_processed, 2),
        total_disposed_tons=round(total_disposed, 2),
        total_remaining_tons=round(total_remaining, 2),
        avg_hazard_class=round(avg_hazard, 2),
        line_utilization=kpi.line_utilization,
        plan_completion_percent=kpi.plan_completion_percent,
        measurements_count=db.query(EnvironmentalMeasurement).count(),
        operations_count=db.query(WasteOperation).count(),
    )


@router.get("/batches/{batch_id}/balance", response_model=BatchBalanceOut)
def get_batch_balance_reporting(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    return BatchBalanceOut(**batch_balance(db, batch))


@router.get("/summary/balances", response_model=list[BatchBalanceOut])
def summary_balances(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    return [
        BatchBalanceOut(**batch_balance(db, b))
        for b in db.query(WasteBatch).order_by(WasteBatch.code).all()
    ]


@router.get("/operations", response_model=list[WasteOperationOut])
def list_operations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    rows = (
        db.query(WasteOperation)
        .order_by(WasteOperation.operation_at.desc())
        .limit(100)
        .all()
    )
    return [_op_out(op) for op in rows]


@router.get("/measurements", response_model=list[MeasurementOut])
def list_measurements(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    return (
        db.query(EnvironmentalMeasurement)
        .order_by(EnvironmentalMeasurement.measured_at.desc())
        .limit(100)
        .all()
    )


@router.post("/measurements", response_model=MeasurementOut, status_code=201)
def add_measurement(
    body: MeasurementCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ecologist", "admin")),
):
    if not db.query(Organization).filter(Organization.id == body.organization_id).first():
        raise HTTPException(404, "Организация не найдена")
    m = EnvironmentalMeasurement(
        organization_id=body.organization_id,
        parameter=body.parameter,
        value=body.value,
        unit=body.unit,
        batch_id=body.batch_id,
        measured_at=datetime.utcnow(),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/summary/by-hazard")
def summary_by_hazard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    rows = (
        db.query(WasteBatch.hazard_class, func.count(), func.sum(WasteBatch.volume_tons))
        .group_by(WasteBatch.hazard_class)
        .all()
    )
    return [
        {"hazard_class": r[0], "batch_count": r[1], "volume_tons": round(float(r[2] or 0), 2)}
        for r in rows
    ]
