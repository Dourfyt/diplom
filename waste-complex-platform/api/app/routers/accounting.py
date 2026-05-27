"""API модуля учёта поступления и классификации (Корчагин Д.Е.)."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BatchDocument, User, WasteBatch, WasteOperation, WasteType
from app.schemas import (
    BatchBalanceOut,
    BatchClassify,
    BatchCreate,
    BatchOut,
    BatchReject,
    OperationCreate,
    WasteOperationOut,
)
from app.services.audit import log_action
from app.services.monitoring_sync import ensure_batch_stages
from app.services.planner import compute_priority, hours_until_deadline
from app.services.rbac import require_roles
from app.services.waste_balance import batch_balance, record_operation

router = APIRouter(tags=["accounting"])


def _attach_balance(db: Session, out: BatchOut, batch: WasteBatch) -> BatchOut:
    bal = batch_balance(db, batch)
    out.processed_tons = bal["processed_tons"]
    out.disposed_tons = bal["disposed_tons"]
    out.remaining_tons = bal["remaining_tons"]
    return out


def _batch_out(db: Session, b: WasteBatch) -> BatchOut:
    now = datetime.utcnow()
    out = BatchOut.model_validate(b)
    out.priority_score = compute_priority(b, now)
    out.storage_risk_hours = hours_until_deadline(b, now)
    return _attach_balance(db, out, b)


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


def _resolve_org_id(db: Session, batch: WasteBatch) -> int:
    if batch.organization_id:
        return batch.organization_id
    row = db.query(WasteBatch.organization_id).filter(WasteBatch.organization_id.isnot(None)).first()
    if row and row[0]:
        return row[0]
    raise HTTPException(400, "Для партии не задана organization_id")


@router.get("/batches", response_model=list[BatchOut])
def list_batches(
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    source_department: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    q = db.query(WasteBatch)
    if status:
        q = q.filter(WasteBatch.status == status)
    if date_from:
        q = q.filter(WasteBatch.received_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(WasteBatch.received_at <= datetime.fromisoformat(date_to))
    if source_department:
        q = q.filter(WasteBatch.source_department == source_department)

    if current_user.role == "chief":
        if status and status != "accepted":
            raise HTTPException(403, "Роль chief может просматривать только партии со статусом accepted")
        q = q.filter(WasteBatch.status == "accepted")

    return [_batch_out(db, b) for b in q.order_by(WasteBatch.received_at.desc()).all()]


@router.get("/batches/{batch_id}/balance", response_model=BatchBalanceOut)
def get_batch_balance(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    return BatchBalanceOut(**batch_balance(db, batch))


@router.post("/batches", response_model=BatchOut, status_code=201)
def register_batch(
    body: BatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("operator")),
):
    if db.query(WasteBatch).filter(WasteBatch.code == body.code).first():
        raise HTTPException(400, f"Партия с кодом {body.code} уже существует")
    wt = None
    if body.waste_type_id:
        wt = db.query(WasteType).filter(WasteType.id == body.waste_type_id).first()
    batch = WasteBatch(
        code=body.code,
        name=body.name,
        fkko_code=body.fkko_code or (wt.fkko_code if wt else ""),
        hazard_class=body.hazard_class,
        volume=body.volume if body.volume is not None else body.volume_tons,
        volume_unit=body.volume_unit,
        volume_tons=body.volume_tons,
        storage_deadline_hours=body.storage_deadline_hours,
        route_codes=body.route_codes,
        economic_value=body.economic_value,
        organization_id=body.organization_id,
        waste_type_id=body.waste_type_id,
        source_department=body.source_department,
        classification_note=body.classification_note,
        status="accepted",
        qr_token=secrets.token_hex(8),
    )
    db.add(batch)
    db.flush()
    db.add(
        BatchDocument(
            batch_id=batch.id,
            doc_type="acceptance_act",
            doc_number=f"АП-{batch.code}",
        )
    )
    if body.organization_id:
        db.add(
            WasteOperation(
                organization_id=body.organization_id,
                waste_type_id=body.waste_type_id,
                batch_id=batch.id,
                user_id=current_user.id,
                operation_type="receipt",
                quantity_tons=body.volume_tons,
                notes=f"Поступление партии {body.code}",
            )
        )
    log_action(
        db,
        user=current_user,
        action="create_batch",
        entity_type="batch",
        entity_id=batch.id,
        details=f"Партия {batch.code}, объем={body.volume}{body.volume_unit}, tons={body.volume_tons}",
    )
    db.commit()
    db.refresh(batch)
    ensure_batch_stages(db, batch.id)
    return _batch_out(db, batch)


@router.patch("/batches/{batch_id}/classify", response_model=BatchOut)
def classify_batch(
    batch_id: int,
    body: BatchClassify,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ecologist", "admin")),
):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    old_hazard = batch.hazard_class
    batch.hazard_class = body.hazard_class
    if body.fkko_code:
        batch.fkko_code = body.fkko_code
    if body.route_codes:
        batch.route_codes = body.route_codes
    batch.classification_note = body.classification_note
    batch.status = "classified"

    db.add(
        WasteOperation(
            organization_id=_resolve_org_id(db, batch),
            waste_type_id=batch.waste_type_id,
            batch_id=batch.id,
            user_id=current_user.id,
            operation_type="classify",
            quantity_tons=0.0,
            old_hazard_class=old_hazard,
            new_hazard_class=body.hazard_class,
            notes=body.classification_note or "Классификация партии",
        )
    )
    log_action(
        db,
        user=current_user,
        action="classify",
        entity_type="batch",
        entity_id=batch.id,
        details=f"hazard {old_hazard}->{body.hazard_class}",
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)


@router.patch("/batches/{batch_id}/reject", response_model=BatchOut)
def reject_batch(
    batch_id: int,
    body: BatchReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ecologist", "admin")),
):
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    batch.status = "rejected"
    batch.classification_note = body.reason
    db.add(
        WasteOperation(
            organization_id=_resolve_org_id(db, batch),
            waste_type_id=batch.waste_type_id,
            batch_id=batch.id,
            user_id=current_user.id,
            operation_type="reject",
            quantity_tons=0.0,
            old_hazard_class=batch.hazard_class,
            new_hazard_class=batch.hazard_class,
            notes=body.reason,
        )
    )
    log_action(
        db,
        user=current_user,
        action="reject",
        entity_type="batch",
        entity_id=batch.id,
        details=body.reason,
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)


@router.get("/batches/{batch_id}/classification-history", response_model=list[WasteOperationOut])
def classification_history(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    ops = (
        db.query(WasteOperation)
        .filter(
            WasteOperation.batch_id == batch_id,
            WasteOperation.operation_type.in_(["classify", "reject"]),
        )
        .order_by(WasteOperation.operation_at.desc())
        .all()
    )
    return [_op_out(op) for op in ops]


@router.get("/batches/{batch_id}/documents")
def list_documents(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    docs = db.query(BatchDocument).filter(BatchDocument.batch_id == batch_id).all()
    return [
        {"id": d.id, "doc_type": d.doc_type, "doc_number": d.doc_number, "created_at": d.created_at}
        for d in docs
    ]


@router.get("/operations", response_model=list[WasteOperationOut])
def list_operations(
    batch_id: int | None = Query(None),
    operation_type: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("chief", "ecologist", "admin")),
):
    q = db.query(WasteOperation).order_by(WasteOperation.operation_at.desc())
    if batch_id is not None:
        q = q.filter(WasteOperation.batch_id == batch_id)
    if operation_type:
        q = q.filter(WasteOperation.operation_type == operation_type)
    return [_op_out(op) for op in q.limit(300).all()]


@router.post("/operations", response_model=WasteOperationOut, status_code=201)
def create_operation(
    body: OperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    try:
        op = record_operation(
            db,
            batch_id=body.batch_id,
            operation_type=body.operation_type,
            quantity_tons=body.quantity_tons,
            organization_id=body.organization_id,
            user_id=current_user.id,
            notes=body.notes or f"{body.operation_type} {body.quantity_tons} т",
        )
        log_action(
            db,
            user=current_user,
            action=body.operation_type,
            entity_type="batch",
            entity_id=body.batch_id,
            details=f"{body.quantity_tons} т",
        )
        db.commit()
        db.refresh(op)
        return _op_out(op)
    except LookupError:
        raise HTTPException(404, "Партия не найдена") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
