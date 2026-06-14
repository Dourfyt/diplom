"""Импорт каталога ФККО из CSV (fkko_full.csv)."""

from __future__ import annotations

import csv
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import WasteType

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "fkko_full.csv"


def _registration_allowed(hazard_class: int) -> bool:
    return hazard_class in (1, 2, 3, 4, 5)


def import_fkko_csv(db: Session, csv_path: Path | str) -> dict[str, int]:
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Файл не найден: {path}")

    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            code = (row.get("code") or "").strip()
            name = (row.get("name") or "").strip()
            if not code or not name:
                continue
            rows.append(row)

    if not rows:
        return {"total": 0, "created": 0, "updated": 0}

    by_code = {row.code: row for row in db.query(WasteType).all()}

    created = 0
    updated = 0
    for row in rows:
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()[:256]
        fkko_code = (row.get("fkko_code") or "").strip()[:32]
        description = (row.get("description") or "").strip()
        try:
            hazard_class = int((row.get("hazard_class") or "0").strip())
        except ValueError:
            hazard_class = 0

        item = by_code.get(code)
        if item is None:
            db.add(
                WasteType(
                    code=code,
                    name=name,
                    fkko_code=fkko_code,
                    hazard_class=hazard_class,
                    description=description,
                )
            )
            created += 1
            continue

        item.name = name
        item.fkko_code = fkko_code
        item.hazard_class = hazard_class
        item.description = description
        updated += 1

    db.commit()
    return {"total": len(rows), "created": created, "updated": updated}


def registration_allowed_for(hazard_class: int) -> bool:
    return _registration_allowed(hazard_class)
