"""Лёгкие миграции схемы без Alembic (для дипломного прототипа)."""

from sqlalchemy import inspect, text

from app.database import engine


def _planstatus_labels(conn) -> list[str]:
    rows = conn.execute(
        text(
            "SELECT e.enumlabel FROM pg_enum e "
            "JOIN pg_type t ON e.enumtypid = t.oid "
            "WHERE t.typname = 'planstatus' "
            "ORDER BY e.enumsortorder"
        )
    ).fetchall()
    return [r[0] for r in rows]


def _migrate_published_to_approved(conn) -> None:
    """published/PUBLISHED → approved/APPROVED с учётом регистра enum в PostgreSQL."""
    labels = _planstatus_labels(conn)
    by_lower = {lb.lower(): lb for lb in labels}

    published = by_lower.get("published")
    approved = by_lower.get("approved")

    if not published:
        return

    if approved:
        conn.execute(
            text(
                f"UPDATE schedule_plans SET status = '{approved}' "
                f"WHERE status::text = '{published}'"
            )
        )
        return

    # Тот же регистр, что у PUBLISHED: PUBLISHED → APPROVED, published → approved
    new_label = "APPROVED" if published.isupper() else "approved"
    conn.execute(
        text(f"ALTER TYPE planstatus RENAME VALUE '{published}' TO '{new_label}'")
    )


def migrate_schema():
    insp = inspect(engine)
    if "schedule_plans" not in insp.get_table_names():
        return

    cols = {c["name"] for c in insp.get_columns("schedule_plans")}

    with engine.begin() as conn:
        if "version_no" not in cols:
            conn.execute(
                text("ALTER TABLE schedule_plans ADD COLUMN version_no INTEGER DEFAULT 1")
            )
        if "approved_at" not in cols:
            conn.execute(
                text("ALTER TABLE schedule_plans ADD COLUMN approved_at TIMESTAMP")
            )
        if "published_at" in cols and "approved_at" in cols:
            conn.execute(
                text(
                    "UPDATE schedule_plans SET approved_at = published_at "
                    "WHERE approved_at IS NULL AND published_at IS NOT NULL"
                )
            )

        _migrate_published_to_approved(conn)

        conn.execute(
            text("UPDATE schedule_plans SET version_no = 1 WHERE version_no IS NULL")
        )

    _migrate_batch_columns()


def _migrate_batch_columns():
    insp = inspect(engine)
    if "waste_batches" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("waste_batches")}
    alters = [
        ("organization_id", "INTEGER"),
        ("waste_type_id", "INTEGER"),
        ("source_department", "VARCHAR(128) DEFAULT ''"),
        ("qr_token", "VARCHAR(64) DEFAULT ''"),
        ("classification_note", "TEXT DEFAULT ''"),
        ("volume", "FLOAT DEFAULT 0"),
        ("volume_unit", "VARCHAR(8) DEFAULT 't'"),
    ]
    with engine.begin() as conn:
        for name, typedef in alters:
            if name not in cols:
                conn.execute(text(f"ALTER TABLE waste_batches ADD COLUMN {name} {typedef}"))
        if "source_module" not in {c["name"] for c in insp.get_columns("notifications")}:
            try:
                conn.execute(
                    text(
                        "ALTER TABLE notifications ADD COLUMN source_module VARCHAR(32) DEFAULT 'planning'"
                    )
                )
            except Exception:
                pass
    _migrate_operations_columns()
    _ensure_audit_logs()


def _migrate_operations_columns():
    insp = inspect(engine)
    if "waste_operations" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("waste_operations")}
    alters = [
        ("user_id", "INTEGER"),
        ("old_hazard_class", "INTEGER"),
        ("new_hazard_class", "INTEGER"),
    ]
    with engine.begin() as conn:
        for name, typedef in alters:
            if name not in cols:
                conn.execute(text(f"ALTER TABLE waste_operations ADD COLUMN {name} {typedef}"))


def _ensure_audit_logs():
    insp = inspect(engine)
    if "audit_logs" in insp.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE audit_logs (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NULL REFERENCES users(id),
                    action VARCHAR(64) NOT NULL,
                    entity_type VARCHAR(64) DEFAULT '',
                    entity_id INTEGER NULL,
                    details TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)"))
