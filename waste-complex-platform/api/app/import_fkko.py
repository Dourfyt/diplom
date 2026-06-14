"""CLI: python -m app.import_fkko [path/to/fkko_full.csv]"""

from __future__ import annotations

import sys
from pathlib import Path

from app.database import SessionLocal
from app.migrate import migrate_schema
from app.services.fkko_import import DEFAULT_CSV, import_fkko_csv


def main() -> None:
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    migrate_schema()
    db = SessionLocal()
    try:
        result = import_fkko_csv(db, csv_path)
        print(
            f"FKKO import OK: total={result['total']}, "
            f"created={result['created']}, updated={result['updated']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
