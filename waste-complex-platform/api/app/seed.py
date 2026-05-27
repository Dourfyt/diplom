"""Единая инициализация БД комплекса: все модули."""

import secrets
import time
from datetime import datetime, timedelta

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.migrate import migrate_schema
from app.models import (
    EnvironmentalMeasurement,
    Organization,
    PlanStatus,
    ProcessingStage,
    ProductionLine,
    RoutingOperation,
    User,
    WasteBatch,
    WasteOperation,
    WasteType,
)
from app.services.monitoring_sync import ensure_batch_stages, sync_stages_from_plan
from app.services.waste_balance import record_operation
from app.services.notifications import check_and_create_notifications
from app.services.planner import build_schedule
from app.services.auth import hash_password


def wait_for_db(max_attempts: int = 30):
    for i in range(max_attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("PostgreSQL недоступен")


def seed():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        if db.query(ProductionLine).count() > 0:
            print("Seed: данные комплекса уже загружены.")
            return

        org = Organization(
            name='ООО "ЭкоПереработка"',
            address="г. Москва, промзона Северная, 12",
            email="eco@example.ru",
            phone="+7 (495) 000-00-00",
        )
        db.add(org)
        db.flush()

        users = [
            User(
                email="operator@eco.local",
                password_hash=hash_password("operator123"),
                full_name="Оператор склада",
                role="operator",
                is_active=True,
            ),
            User(
                email="chief@eco.local",
                password_hash=hash_password("chief123"),
                full_name="Начальник склада",
                role="chief",
                is_active=True,
            ),
            User(
                email="ecologist@eco.local",
                password_hash=hash_password("ecologist123"),
                full_name="Эколог",
                role="ecologist",
                is_active=True,
            ),
            User(
                email="admin@eco.local",
                password_hash=hash_password("admin123"),
                full_name="Администратор",
                role="admin",
                is_active=True,
            ),
        ]
        db.add_all(users)
        db.flush()

        waste_types = [
            WasteType(
                code="WT-SLUDGE",
                name="Шламы металлургические",
                fkko_code="4 12 110 01 11 4",
                hazard_class=4,
            ),
            WasteType(
                code="WT-OIL",
                name="Нефтешлам",
                fkko_code="4 06 200 03 51 3",
                hazard_class=3,
            ),
            WasteType(
                code="WT-CHEM",
                name="Химические остатки",
                fkko_code="4 14 200 01 11 5",
                hazard_class=5,
            ),
        ]
        db.add_all(waste_types)
        db.flush()

        l1 = ProductionLine(
            code="L1",
            name="Линия сушки и сепарации",
            line_type="drying_separation",
            capacity_t_per_hour=4.0,
        )
        l2 = ProductionLine(
            code="L2",
            name="Линия термообезвреживания",
            line_type="thermal",
            capacity_t_per_hour=3.0,
        )
        db.add_all([l1, l2])

        db.add_all(
            [
                RoutingOperation(
                    code="DRY_SEP",
                    name="Сушка и сепарация",
                    line_code="L1",
                    base_duration_hours=2.0,
                    output_ratio=0.88,
                    loss_ratio=0.12,
                    sequence_order=1,
                ),
                RoutingOperation(
                    code="THERMAL",
                    name="Термообезвреживание",
                    line_code="L2",
                    base_duration_hours=2.5,
                    output_ratio=0.80,
                    loss_ratio=0.20,
                    sequence_order=2,
                ),
            ]
        )

        db.add_all(
            [
                ProcessingStage(
                    code="ST-RECEIPT",
                    name="Приёмка и хранение",
                    sequence_order=1,
                    norm_hours=1.0,
                    line_code="",
                ),
                ProcessingStage(
                    code="ST-L1",
                    name="Сушка / сепарация",
                    sequence_order=2,
                    norm_hours=2.0,
                    line_code="L1",
                ),
                ProcessingStage(
                    code="ST-L2",
                    name="Термообезвреживание",
                    sequence_order=3,
                    norm_hours=2.5,
                    line_code="L2",
                ),
                ProcessingStage(
                    code="ST-DISPOSAL",
                    name="Вывоз вторичного сырья",
                    sequence_order=4,
                    norm_hours=0.5,
                    line_code="",
                ),
            ]
        )

        now = datetime.utcnow()
        batches = [
            WasteBatch(
                code="P1",
                name="Шламы металлургические",
                fkko_code="4 12 110 01 11 4",
                hazard_class=4,
                volume=12.0,
                volume_unit="t",
                volume_tons=12.0,
                storage_deadline_hours=72,
                received_at=now - timedelta(hours=60),
                route_codes="L1,L2",
                economic_value=450.0,
                organization_id=org.id,
                waste_type_id=waste_types[0].id,
                source_department="Цех №1",
                qr_token=secrets.token_hex(8),
            ),
            WasteBatch(
                code="P2",
                name="Нефтешлам 3 класса",
                fkko_code="4 06 200 03 51 3",
                hazard_class=3,
                volume=8000.0,
                volume_unit="kg",
                volume_tons=8.0,
                storage_deadline_hours=12,
                received_at=now - timedelta(hours=8),
                route_codes="L1",
                economic_value=320.0,
                organization_id=org.id,
                waste_type_id=waste_types[1].id,
                source_department="Цех №2",
                qr_token=secrets.token_hex(8),
            ),
            WasteBatch(
                code="P3",
                name="Вскрышные породы",
                fkko_code="5 01 000 00 00 0",
                hazard_class=4,
                volume=20.0,
                volume_unit="t",
                volume_tons=20.0,
                storage_deadline_hours=96,
                received_at=now - timedelta(hours=24),
                route_codes="L1,L2",
                economic_value=180.0,
                organization_id=org.id,
                source_department="Карьер",
                qr_token=secrets.token_hex(8),
            ),
            WasteBatch(
                code="P4",
                name="Химические остатки",
                fkko_code="4 14 200 01 11 5",
                hazard_class=5,
                volume=5000.0,
                volume_unit="kg",
                volume_tons=5.0,
                storage_deadline_hours=48,
                received_at=now - timedelta(hours=40),
                route_codes="L2",
                economic_value=520.0,
                organization_id=org.id,
                waste_type_id=waste_types[2].id,
                source_department="Лаборатория",
                qr_token=secrets.token_hex(8),
            ),
            WasteBatch(
                code="P5",
                name="Окалина стальная",
                fkko_code="4 12 110 01 12 4",
                hazard_class=4,
                volume=15.0,
                volume_unit="t",
                volume_tons=15.0,
                storage_deadline_hours=80,
                received_at=now - timedelta(hours=12),
                route_codes="L1,L2",
                economic_value=390.0,
                organization_id=org.id,
                qr_token=secrets.token_hex(8),
            ),
            WasteBatch(
                code="P6",
                name="Отходы обогащения",
                fkko_code="5 02 100 01 11 4",
                hazard_class=4,
                volume=10000.0,
                volume_unit="kg",
                volume_tons=10.0,
                storage_deadline_hours=5,
                received_at=now - timedelta(hours=10),
                route_codes="L1",
                economic_value=210.0,
                organization_id=org.id,
                qr_token=secrets.token_hex(8),
            ),
        ]
        db.add_all(batches)
        db.commit()

        for b in batches:
            ensure_batch_stages(db, b.id)
            db.add(
                WasteOperation(
                    organization_id=org.id,
                    waste_type_id=b.waste_type_id,
                    batch_id=b.id,
                    operation_type="receipt",
                    quantity_tons=b.volume_tons,
                    user_id=users[0].id,
                    notes=f"Поступление {b.code}",
                )
            )
        db.commit()

        # Демо: частичная переработка и вывоз (журнал движения)
        record_operation(
            db,
            batch_id=batches[0].id,
            operation_type="processing",
            quantity_tons=8.0,
            organization_id=org.id,
            notes="Переработка L1+L2 (демо)",
        )
        record_operation(
            db,
            batch_id=batches[0].id,
            operation_type="disposal",
            quantity_tons=2.0,
            organization_id=org.id,
            notes="Вывоз на утилизацию (демо)",
        )
        record_operation(
            db,
            batch_id=batches[1].id,
            operation_type="processing",
            quantity_tons=5.0,
            organization_id=org.id,
            notes="Частичная переработка (демо)",
        )
        db.commit()

        db.add_all(
            [
                EnvironmentalMeasurement(
                    organization_id=org.id,
                    parameter="Выбросы пыли",
                    value=18.5,
                    unit="мг/м³",
                    measured_at=now - timedelta(hours=2),
                ),
                EnvironmentalMeasurement(
                    organization_id=org.id,
                    parameter="pH сточных вод",
                    value=7.2,
                    unit="pH",
                    measured_at=now - timedelta(hours=1),
                ),
            ]
        )
        db.commit()

        plan = build_schedule(db, name="Демонстрационный сменный план", horizon_hours=8.0)
        plan.status = PlanStatus.APPROVED
        plan.approved_at = datetime.utcnow()
        db.commit()
        sync_stages_from_plan(db, plan.id)
        check_and_create_notifications(db, plan.id)

        print(
            "Seed OK: организация, 3 вида отходов, 6 партий, 4 этапа мониторинга, "
            f"план id={plan.id}, API: /docs"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
