"""Баланс партии по журналу waste_operations."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import WasteBatch, WasteOperation

RECEIPT_TYPES = frozenset({"receipt"})
PROCESSED_TYPES = frozenset({"processing"})
DISPOSED_TYPES = frozenset({"disposal", "export", "transfer"})


def sums_for_batch(db: Session, batch_id: int) -> tuple[float, float, float]:
    rows = (
        db.query(WasteOperation.operation_type, func.coalesce(func.sum(WasteOperation.quantity_tons), 0.0))
        .filter(WasteOperation.batch_id == batch_id)
        .group_by(WasteOperation.operation_type)
        .all()
    )
    processed = 0.0
    disposed = 0.0
    for op_type, total in rows:
        t = float(total)
        if op_type in PROCESSED_TYPES:
            processed += t
        elif op_type in DISPOSED_TYPES:
            disposed += t
    return processed, disposed


def batch_balance(db: Session, batch: WasteBatch) -> dict:
    processed, disposed = sums_for_batch(db, batch.id)
    received = batch.volume_tons
    remaining = round(max(0.0, received - processed - disposed), 3)
    return {
        "batch_id": batch.id,
        "batch_code": batch.code,
        "received_tons": round(received, 3),
        "processed_tons": round(processed, 3),
        "disposed_tons": round(disposed, 3),
        "remaining_tons": remaining,
    }


def assert_can_record(db: Session, batch: WasteBatch, operation_type: str, quantity_tons: float) -> None:
    if operation_type in PROCESSED_TYPES | DISPOSED_TYPES:
        bal = batch_balance(db, batch)
        if quantity_tons > bal["remaining_tons"] + 1e-6:
            raise ValueError(
                f"Превышен остаток партии: запрошено {quantity_tons} т, "
                f"доступно {bal['remaining_tons']} т"
            )


def refresh_batch_status(db: Session, batch: WasteBatch) -> None:
    """Обновить статус партии по фактическим операциям."""
    bal = batch_balance(db, batch)
    if bal["remaining_tons"] <= 1e-6 and (bal["processed_tons"] > 0 or bal["disposed_tons"] > 0):
        batch.status = "done"
    elif bal["processed_tons"] > 0:
        batch.status = "processing"
    elif batch.status not in ("classified", "accepted"):
        pass


def record_operation(
    db: Session,
    *,
    batch_id: int,
    operation_type: str,
    quantity_tons: float,
    organization_id: int | None = None,
    user_id: int | None = None,
    old_hazard_class: int | None = None,
    new_hazard_class: int | None = None,
    notes: str = "",
) -> WasteOperation:
    batch = db.get(WasteBatch, batch_id)
    if not batch:
        raise LookupError("Партия не найдена")
    org_id = organization_id or batch.organization_id
    if not org_id:
        raise ValueError("Укажите organization_id или привяжите партию к организации")

    assert_can_record(db, batch, operation_type, quantity_tons)

    op = WasteOperation(
        organization_id=org_id,
        waste_type_id=batch.waste_type_id,
        batch_id=batch.id,
        operation_type=operation_type,
        quantity_tons=round(quantity_tons, 3),
        user_id=user_id,
        old_hazard_class=old_hazard_class,
        new_hazard_class=new_hazard_class,
        notes=notes,
    )
    db.add(op)
    if operation_type in PROCESSED_TYPES | DISPOSED_TYPES:
        refresh_batch_status(db, batch)
    db.flush()
    return op
