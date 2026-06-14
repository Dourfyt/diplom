"""API модуля учёта поступления и классификации (Корчагин Д.Е.)."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BatchDocument, User, WasteBatch, WasteOperation, WasteType
from app.schemas import (
    BatchBalanceOut,
    BatchClassify,
    BatchCreate,
    BatchDocumentOut,
    BatchOut,
    BatchReject,
    ClassificationHistoryOut,
    OperationCreate,
    WasteOperationOut,
)
from app.services.audit import log_action
from app.services.auth import get_current_user
from app.services.batch_query import apply_batch_filters
from app.services.files import delete_file, resolve_path, save_upload
from app.services.monitoring_sync import ensure_batch_stages
from app.services.planner import compute_priority, hours_until_deadline
from app.services.rbac import require_roles
from app.services.waste_balance import batch_balance, record_operation

router = APIRouter(tags=["accounting"])

DOC_TYPES = {"confirming", "reception_act"}


def _doc_out(doc: BatchDocument) -> BatchDocumentOut:
    return BatchDocumentOut(
        id=doc.id,
        batch_id=doc.batch_id,
        document_type=doc.document_type or doc.doc_type or "confirming",
        file_name=doc.file_name or doc.doc_number or "",
        content_type=doc.content_type or "application/octet-stream",
        file_size=int(doc.file_size or 0),
        uploaded_by=doc.uploaded_by,
        created_at=doc.created_at,
    )


def _attach_balance(db: Session, out: BatchOut, batch: WasteBatch) -> BatchOut:
    bal = batch_balance(db, batch)
    out.processed_tons = bal["processed_tons"]
    out.disposed_tons = bal["disposed_tons"]
    out.remaining_tons = bal["remaining_tons"]
    return out


def _batch_out(db: Session, batch: WasteBatch) -> BatchOut:
    now = datetime.utcnow()
    out = BatchOut.model_validate(batch)
    out.priority_score = compute_priority(batch, now)
    out.storage_risk_hours = hours_until_deadline(batch, now)
    out.documents = [_doc_out(d) for d in batch.documents]
    return _attach_balance(db, out, batch)


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


def _history_out(op: WasteOperation) -> ClassificationHistoryOut:
    return ClassificationHistoryOut(
        operation_type=op.operation_type,
        operation_at=op.operation_at,
        user_id=op.user_id,
        user_name=op.user.full_name if op.user else None,
        old_hazard_class=op.old_hazard_class,
        new_hazard_class=op.new_hazard_class,
        notes=op.notes,
    )


def _resolve_org_id(db: Session, batch: WasteBatch) -> int:
    if batch.organization_id:
        return batch.organization_id
    row = db.query(WasteBatch.organization_id).filter(WasteBatch.organization_id.isnot(None)).first()
    if row and row[0]:
        return row[0]
    raise HTTPException(400, "Для партии не задана organization_id")


def _get_batch_or_404(db: Session, batch_id: int) -> WasteBatch:
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")
    return batch


@router.get("/batches", response_model=list[BatchOut])
def list_batches(
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    source_department: str | None = Query(default=None),
    hazard_class: int | None = Query(default=None),
    overdue_storage: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    q = apply_batch_filters(
        db.query(WasteBatch),
        status=status,
        date_from=date_from,
        date_to=date_to,
        source_department=source_department,
        hazard_class=hazard_class,
        overdue_storage=overdue_storage,
    )
    rows = q.order_by(WasteBatch.received_at.desc()).all()
    return [_batch_out(db, b) for b in rows]


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    return _batch_out(db, _get_batch_or_404(db, batch_id))


@router.get("/batches/{batch_id}/balance", response_model=BatchBalanceOut)
def get_batch_balance(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    batch = _get_batch_or_404(db, batch_id)
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
        composition=body.composition,
        classification_note=body.classification_note,
        status="accepted",
        qr_token=secrets.token_hex(8),
    )
    db.add(batch)
    db.flush()
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
        details=f"Партия {batch.code}, {body.volume}{body.volume_unit}, {body.volume_tons} т",
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
    current_user: User = Depends(require_roles("ecologist")),
):
    batch = _get_batch_or_404(db, batch_id)
    old_hazard = batch.hazard_class
    batch.hazard_class = body.hazard_class
    if body.fkko_code:
        batch.fkko_code = body.fkko_code
    if body.route_codes:
        batch.route_codes = body.route_codes
    batch.classification_note = body.classification_note
    batch.status = "classified"
    note = body.classification_note or "Классификация партии"
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
            notes=note,
        )
    )
    log_action(
        db,
        user=current_user,
        action="classify",
        entity_type="batch",
        entity_id=batch.id,
        details=f"hazard {old_hazard}->{body.hazard_class}; {note}",
    )
    db.commit()
    db.refresh(batch)
    return _batch_out(db, batch)


@router.patch("/batches/{batch_id}/reject", response_model=BatchOut)
def reject_batch(
    batch_id: int,
    body: BatchReject,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ecologist")),
):
    batch = _get_batch_or_404(db, batch_id)
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


@router.get("/batches/{batch_id}/classification-history", response_model=list[ClassificationHistoryOut])
def classification_history(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = _get_batch_or_404(db, batch_id)
    if current_user.role == "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    if current_user.role not in ("chief", "ecologist", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")
    ops = (
        db.query(WasteOperation)
        .filter(
            WasteOperation.batch_id == batch.id,
            WasteOperation.operation_type.in_(["classify", "reject"]),
        )
        .order_by(WasteOperation.operation_at.asc())
        .all()
    )
    return [_history_out(op) for op in ops]


@router.get("/batches/{batch_id}/documents", response_model=list[BatchDocumentOut])
def list_documents(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    _get_batch_or_404(db, batch_id)
    docs = db.query(BatchDocument).filter(BatchDocument.batch_id == batch_id).order_by(BatchDocument.id).all()
    return [_doc_out(d) for d in docs]


@router.post("/batches/{batch_id}/documents", response_model=BatchDocumentOut, status_code=201)
async def upload_document(
    batch_id: int,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("operator")),
):
    if document_type not in DOC_TYPES:
        raise HTTPException(400, detail=f"document_type должен быть один из: {sorted(DOC_TYPES)}")
    batch = _get_batch_or_404(db, batch_id)
    storage_path, file_name, size = await save_upload(
        file, subdir=f"batch_documents/{batch.id}"
    )
    doc = BatchDocument(
        batch_id=batch.id,
        document_type=document_type,
        doc_type=document_type,
        file_name=file_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=size,
        storage_path=storage_path,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    log_action(
        db,
        user=current_user,
        action="upload_document",
        entity_type="batch_document",
        entity_id=batch.id,
        details=f"{document_type}: {file_name}",
    )
    db.commit()
    db.refresh(doc)
    return _doc_out(doc)


@router.get("/batches/{batch_id}/documents/{doc_id}/download")
def download_document(
    batch_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    doc = (
        db.query(BatchDocument)
        .filter(BatchDocument.id == doc_id, BatchDocument.batch_id == batch_id)
        .first()
    )
    if not doc or not doc.storage_path:
        raise HTTPException(404, "Документ не найден")
    path = resolve_path(doc.storage_path)
    return FileResponse(
        path,
        media_type=doc.content_type or "application/octet-stream",
        filename=doc.file_name or path.name,
    )


@router.delete("/batches/{batch_id}/documents/{doc_id}")
def delete_document(
    batch_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    doc = (
        db.query(BatchDocument)
        .filter(BatchDocument.id == doc_id, BatchDocument.batch_id == batch_id)
        .first()
    )
    if not doc:
        raise HTTPException(404, "Документ не найден")
    delete_file(doc.storage_path)
    db.delete(doc)
    log_action(
        db,
        user=current_user,
        action="delete_document",
        entity_type="batch_document",
        entity_id=doc_id,
        details=f"batch={batch_id}",
    )
    db.commit()
    return {"ok": True}


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
    current_user: User = Depends(require_roles("chief")),
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
            action="create_operation",
            entity_type="batch",
            entity_id=body.batch_id,
            details=f"{body.operation_type} {body.quantity_tons} т",
        )
        db.commit()
        db.refresh(op)
        return _op_out(op)
    except LookupError:
        raise HTTPException(404, "Партия не найдена") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
