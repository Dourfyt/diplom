"""Сохранение загруженных файлов (документы партий, отчёты)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}


def _safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\- ()]", "_", base)
    return base[:255] or "file.bin"


def validate_upload(file: UploadFile) -> None:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            detail=f"Недопустимый формат файла. Разрешены: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        # допускаем octet-stream для docx с некоторых клиентов
        if file.content_type not in ("application/octet-stream",):
            raise HTTPException(400, detail=f"Недопустимый content-type: {file.content_type}")


async def read_limited(file: UploadFile, max_bytes: int | None = None) -> bytes:
    limit = max_bytes or settings.max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(413, detail=f"Файл превышает лимит {limit // (1024 * 1024)} MB")
        chunks.append(chunk)
    return b"".join(chunks)


async def save_upload(
    file: UploadFile,
    *,
    subdir: str,
    max_bytes: int | None = None,
    allowed_extensions: set[str] | None = None,
) -> tuple[str, str, int]:
    """Возвращает (storage_path относительно root, file_name, size)."""
    ext = Path(file.filename or "").suffix.lower()
    if allowed_extensions is not None:
        if ext not in allowed_extensions:
            raise HTTPException(
                400,
                detail=f"Недопустимый формат. Разрешены: {', '.join(sorted(allowed_extensions))}",
            )
    else:
        validate_upload(file)
    data = await read_limited(file, max_bytes=max_bytes)
    root = Path(settings.file_storage_root)
    target_dir = root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_filename(file.filename or "upload.bin")
    stored_name = f"{uuid.uuid4().hex}_{safe}"
    abs_path = target_dir / stored_name
    abs_path.write_bytes(data)
    rel = str(Path(subdir) / stored_name)
    content_type = file.content_type or "application/octet-stream"
    return rel, safe, len(data)


def resolve_path(storage_path: str) -> Path:
    root = Path(settings.file_storage_root).resolve()
    path = (root / storage_path).resolve()
    if not str(path).startswith(str(root)):
        raise HTTPException(400, detail="Некорректный путь к файлу")
    if not path.is_file():
        raise HTTPException(404, detail="Файл не найден")
    return path


def delete_file(storage_path: str | None) -> None:
    if not storage_path:
        return
    try:
        path = resolve_path(storage_path)
        path.unlink(missing_ok=True)
    except HTTPException:
        pass
