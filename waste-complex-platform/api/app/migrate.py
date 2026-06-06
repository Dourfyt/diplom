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
    _migrate_wpf_client_schema()


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


def _migrate_wpf_client_schema():
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    if "waste_batches" in tables:
        cols = {c["name"] for c in insp.get_columns("waste_batches")}
        with engine.begin() as conn:
            if "composition" not in cols:
                conn.execute(text("ALTER TABLE waste_batches ADD COLUMN composition TEXT DEFAULT ''"))

    if "batch_documents" in tables:
        cols = {c["name"] for c in insp.get_columns("batch_documents")}
        alters = [
            ("document_type", "VARCHAR(32) DEFAULT 'confirming'"),
            ("file_name", "VARCHAR(255) DEFAULT ''"),
            ("content_type", "VARCHAR(128) DEFAULT ''"),
            ("file_size", "BIGINT DEFAULT 0"),
            ("storage_path", "VARCHAR(512) DEFAULT ''"),
            ("uploaded_by", "INTEGER REFERENCES users(id)"),
        ]
        with engine.begin() as conn:
            for name, typedef in alters:
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE batch_documents ADD COLUMN {name} {typedef}"))
            conn.execute(
                text(
                    "UPDATE batch_documents SET document_type = CASE "
                    "WHEN doc_type IN ('reception_act', 'reception') THEN 'reception_act' "
                    "ELSE 'confirming' END "
                    "WHERE document_type IS NULL OR document_type = ''"
                )
            )

    if "departments" not in tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE departments (
                        id SERIAL PRIMARY KEY,
                        code VARCHAR(32) UNIQUE NOT NULL,
                        name VARCHAR(128) UNIQUE NOT NULL
                    )
                    """
                )
            )
            for code, name in (("CEH-1", "Цех-1"), ("CEH-2", "Цех-2"), ("CEH-3", "Цех-3")):
                conn.execute(
                    text(
                        "INSERT INTO departments (code, name) VALUES (:code, :name) "
                        "ON CONFLICT (code) DO NOTHING"
                    ),
                    {"code": code, "name": name},
                )

    if "stored_reports" not in tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE stored_reports (
                        id SERIAL PRIMARY KEY,
                        report_type VARCHAR(64) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        date_from DATE NULL,
                        date_to DATE NULL,
                        filters_json TEXT DEFAULT '{}',
                        file_name VARCHAR(255) NOT NULL,
                        content_type VARCHAR(128) DEFAULT '',
                        file_size BIGINT DEFAULT 0,
                        storage_path VARCHAR(512) NOT NULL,
                        generated_by INTEGER NULL REFERENCES users(id),
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
            )

    _ensure_user_devices()


def _ensure_user_devices():
    insp = inspect(engine)
    if "user_devices" in insp.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE user_devices (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    device_id VARCHAR(128) NOT NULL,
                    platform VARCHAR(32) DEFAULT 'android',
                    fcm_token VARCHAR(512) NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_devices_user_id ON user_devices(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_user_devices_device_id ON user_devices(device_id)"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_user_devices_user_device "
                "ON user_devices(user_id, device_id)"
            )
        )
