"""Отклонения по этапам переработки с прикреплением фото."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import BatchStageProgress, ProductionLine, StageDeviation, WasteBatch
from app.schemas import DeviationOut, DeviationStatusUpdate
from app.services.files import delete_file, resolve_path, save_upload

router = APIRouter(tags=["monitoring", "deviations"])

DEVIATION_TYPES = frozenset({"delay", "quality", "equipment", "safety", "other"})
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
PHOTO_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "application/octet-stream"}
)


def _photo_url(deviation_id: int) -> str:
    return f"/api/v1/deviations/{deviation_id}/photo"


def _to_out(row: StageDeviation) -> DeviationOut:
    batch = row.batch
    stage_code = None
    if row.progress and row.progress.stage:
        stage_code = row.progress.stage.code
    return DeviationOut(
        id=row.id,
        batch_id=row.batch_id,
        batch_code=batch.code if batch else None,
        progress_id=row.progress_id,
        stage_id=row.stage_id,
        stage_code=stage_code,
        line_id=row.line_id,
        deviation_type=row.deviation_type,
        comment=row.comment,
        operator_name=row.operator_name,
        deviation_percent=row.deviation_percent,
        status=row.status,
        file_name=row.file_name,
        content_type=row.content_type,
        file_size=row.file_size,
        photo_url=_photo_url(row.id),
        created_at=row.created_at,
    )


def _get_or_404(db: Session, deviation_id: int) -> StageDeviation:
    row = (
        db.query(StageDeviation)
        .options(
            joinedload(StageDeviation.batch),
            joinedload(StageDeviation.progress).joinedload(BatchStageProgress.stage),
        )
        .filter(StageDeviation.id == deviation_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Отклонение не найдено")
    return row


@router.get("/deviations", response_model=list[DeviationOut])
def list_deviations(
    batch_id: int | None = Query(default=None),
    progress_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = (
        db.query(StageDeviation)
        .options(
            joinedload(StageDeviation.batch),
            joinedload(StageDeviation.progress).joinedload(BatchStageProgress.stage),
        )
        .order_by(StageDeviation.created_at.desc())
    )
    if batch_id is not None:
        q = q.filter(StageDeviation.batch_id == batch_id)
    if progress_id is not None:
        q = q.filter(StageDeviation.progress_id == progress_id)
    if status is not None:
        q = q.filter(StageDeviation.status == status)
    rows = q.limit(limit).all()
    return [_to_out(r) for r in rows]


@router.get("/deviations/{deviation_id}", response_model=DeviationOut)
def get_deviation(deviation_id: int, db: Session = Depends(get_db)):
    return _to_out(_get_or_404(db, deviation_id))


@router.post("/deviations", response_model=DeviationOut, status_code=201)
async def create_deviation(
    batch_id: int = Form(...),
    photo: UploadFile = File(..., description="Фотография отклонения"),
    progress_id: int | None = Form(default=None),
    stage_id: int | None = Form(default=None),
    line_id: int | None = Form(default=None),
    deviation_type: str = Form(default="other"),
    comment: str = Form(default=""),
    operator_name: str = Form(default="operator"),
    deviation_percent: float | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if deviation_type not in DEVIATION_TYPES:
        raise HTTPException(400, detail=f"deviation_type: {sorted(DEVIATION_TYPES)}")
    batch = db.query(WasteBatch).filter(WasteBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Партия не найдена")

    prog: BatchStageProgress | None = None
    if progress_id is not None:
        prog = (
            db.query(BatchStageProgress)
            .options(joinedload(BatchStageProgress.stage))
            .filter(
                BatchStageProgress.id == progress_id,
                BatchStageProgress.batch_id == batch_id,
            )
            .first()
        )
        if not prog:
            raise HTTPException(404, "Этап партии не найден")
        stage_id = prog.stage_id
        if line_id is None and prog.stage and prog.stage.line_code:
            line = (
                db.query(ProductionLine)
                .filter(ProductionLine.code == prog.stage.line_code)
                .first()
            )
            if line:
                line_id = line.id
        if prog.status not in ("delayed", "done"):
            prog.status = "delayed"
        if deviation_percent is not None:
            prog.deviation_percent = deviation_percent

    if stage_id is not None and progress_id is None:
        prog = (
            db.query(BatchStageProgress)
            .filter(
                BatchStageProgress.batch_id == batch_id,
                BatchStageProgress.stage_id == stage_id,
            )
            .first()
        )
        if prog:
            progress_id = prog.id

    if photo.content_type and photo.content_type not in PHOTO_CONTENT_TYPES:
        raise HTTPException(400, detail=f"Недопустимый тип изображения: {photo.content_type}")

    storage_path, file_name, size = await save_upload(
        photo,
        subdir=f"deviations/{batch_id}",
        max_bytes=10 * 1024 * 1024,
        allowed_extensions=PHOTO_EXTENSIONS,
    )

    row = StageDeviation(
        batch_id=batch_id,
        progress_id=progress_id,
        stage_id=stage_id,
        line_id=line_id,
        deviation_type=deviation_type,
        comment=comment.strip(),
        operator_name=operator_name.strip() or "operator",
        deviation_percent=deviation_percent,
        status="new",
        file_name=file_name,
        content_type=photo.content_type or "image/jpeg",
        file_size=size,
        storage_path=storage_path,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = _get_or_404(db, row.id)
    return _to_out(row)


@router.get("/deviations/{deviation_id}/photo")
def download_deviation_photo(deviation_id: int, db: Session = Depends(get_db)):
    row = _get_or_404(db, deviation_id)
    if not row.storage_path:
        raise HTTPException(404, "Фото не прикреплено")
    path = resolve_path(row.storage_path)
    return FileResponse(path, media_type=row.content_type or "image/jpeg", filename=row.file_name)


@router.patch("/deviations/{deviation_id}", response_model=DeviationOut)
def update_deviation(
    deviation_id: int,
    body: DeviationStatusUpdate,
    db: Session = Depends(get_db),
):
    row = _get_or_404(db, deviation_id)
    row.status = body.status
    if body.comment is not None:
        row.comment = body.comment
    db.commit()
    return _to_out(_get_or_404(db, deviation_id))


@router.delete("/deviations/{deviation_id}", status_code=204)
def delete_deviation(deviation_id: int, db: Session = Depends(get_db)):
    row = _get_or_404(db, deviation_id)
    delete_file(row.storage_path)
    db.delete(row)
    db.commit()
