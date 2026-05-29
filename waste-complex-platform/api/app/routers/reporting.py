"""API модуля отчётности и экологического контроля (Журавлёва М.Е.)."""

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EnvironmentalMeasurement, Organization, StoredReport, User, WasteBatch, WasteOperation
from app.schemas import (
    BatchBalanceOut,
    HazardSummaryOut,
    MeasurementCreate,
    MeasurementOut,
    ReportingDashboard,
    StoredReportOut,
    WasteOperationOut,
)
from app.services.audit import log_action
from app.services.batch_query import count_dashboard_metrics
from app.services.files import delete_file, resolve_path, save_upload
from app.services.kpi import plan_kpi
from app.services.plan_lifecycle import get_active_approved
from app.services.rbac import require_roles
from app.services.waste_balance import batch_balance

router = APIRouter(tags=["reporting"])

REPORT_TYPES = {
    "batches_excel",
    "batch_act_word",
    "classification_excel",
    "hazard_summary",
}
REPORT_EXTENSIONS = {".xlsx", ".docx"}


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


def _report_out(row: StoredReport) -> StoredReportOut:
    return StoredReportOut.model_validate(row)


@router.get("/dashboard", response_model=ReportingDashboard)
def reporting_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    org = db.query(Organization).first()
    batches = db.query(WasteBatch).all()
    processed_batches = sum(1 for b in batches if b.status in ("processing", "done", "classified"))
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
    counters = count_dashboard_metrics(db)
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
        **counters,
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


@router.get("/summary/by-hazard", response_model=list[HazardSummaryOut])
def summary_by_hazard(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    rows = (
        db.query(WasteBatch.hazard_class, func.count(), func.sum(WasteBatch.volume_tons))
        .group_by(WasteBatch.hazard_class)
        .order_by(WasteBatch.hazard_class)
        .all()
    )
    return [
        HazardSummaryOut(
            hazard_class=int(r[0]),
            batch_count=int(r[1]),
            volume_tons=round(float(r[2] or 0), 2),
        )
        for r in rows
    ]


@router.post("/reports", response_model=StoredReportOut, status_code=201)
async def save_report(
    file: UploadFile = File(...),
    report_type: str = Form(...),
    title: str = Form(...),
    date_from: str | None = Form(default=None),
    date_to: str | None = Form(default=None),
    filters_json: str = Form(default="{}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    if report_type not in REPORT_TYPES:
        raise HTTPException(400, detail=f"report_type: {sorted(REPORT_TYPES)}")
    ext = (file.filename or "").lower()
    if not any(ext.endswith(suffix) for suffix in REPORT_EXTENSIONS):
        raise HTTPException(400, detail="Разрешены только .xlsx и .docx")
    try:
        json.loads(filters_json or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(400, detail="filters_json должен быть валидным JSON") from e

    storage_path, file_name, size = await save_upload(
        file, subdir="reports", allowed_extensions=REPORT_EXTENSIONS
    )
    parsed_from = date.fromisoformat(date_from) if date_from else None
    parsed_to = date.fromisoformat(date_to) if date_to else None
    row = StoredReport(
        report_type=report_type,
        title=title.strip(),
        date_from=parsed_from,
        date_to=parsed_to,
        filters_json=filters_json or "{}",
        file_name=file_name,
        content_type=file.content_type
        or (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if file_name.lower().endswith(".xlsx")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        file_size=size,
        storage_path=storage_path,
        generated_by=current_user.id,
    )
    db.add(row)
    log_action(
        db,
        user=current_user,
        action="save_report",
        entity_type="stored_report",
        entity_id=None,
        details=title,
    )
    db.commit()
    db.refresh(row)
    return _report_out(row)


@router.get("/reports", response_model=list[StoredReportOut])
def list_reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    rows = db.query(StoredReport).order_by(StoredReport.created_at.desc()).limit(200).all()
    return [_report_out(r) for r in rows]


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    row = db.get(StoredReport, report_id)
    if not row:
        raise HTTPException(404, "Отчёт не найден")
    path = resolve_path(row.storage_path)
    return FileResponse(
        path,
        media_type=row.content_type or "application/octet-stream",
        filename=row.file_name or path.name,
    )


@router.delete("/reports/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    row = db.get(StoredReport, report_id)
    if not row:
        raise HTTPException(404, "Отчёт не найден")
    delete_file(row.storage_path)
    db.delete(row)
    log_action(
        db,
        user=current_user,
        action="delete_report",
        entity_type="stored_report",
        entity_id=report_id,
        details=row.title,
    )
    db.commit()
    return {"ok": True}
