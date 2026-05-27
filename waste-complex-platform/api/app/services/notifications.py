from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    Notification,
    NotificationStatus,
    ProductionLine,
    ScheduleItem,
    WasteBatch,
)
from app.services.planner import hours_until_deadline


def check_and_create_notifications(db: Session, plan_id: int | None = None) -> list[Notification]:
    now = datetime.utcnow()
    created: list[Notification] = []

    batches = db.query(WasteBatch).all()
    for batch in batches:
        remaining = hours_until_deadline(batch, now)
        # T2: остаток хранения < 6 ч
        if remaining < 6 and remaining >= 0:
            exists = (
                db.query(Notification)
                .filter(
                    Notification.batch_id == batch.id,
                    Notification.trigger_code == "T2",
                    Notification.status != NotificationStatus.ACKNOWLEDGED,
                )
                .first()
            )
            if not exists:
                n = Notification(
                    trigger_code="T2",
                    title=f"Риск просрочки хранения: {batch.code}",
                    message=(
                        f"Партия {batch.code} (класс {batch.hazard_class}): "
                        f"осталось {remaining:.1f} ч до предельного срока хранения."
                    ),
                    batch_id=batch.id,
                    channel="in_app",
                )
                db.add(n)
                created.append(n)

    if plan_id:
        items = db.query(ScheduleItem).filter(ScheduleItem.plan_id == plan_id).all()
        line_load: dict[int, list] = {}
        for item in items:
            line_load.setdefault(item.line_id, []).append(item)

        for line_id, line_items in line_load.items():
            line = db.get(ProductionLine, line_id)
            if not line:
                continue
            # T1: прогноз простоя > 30 мин — упрощённо: разрыв > 0.5 ч между операциями
            sorted_items = sorted(line_items, key=lambda x: x.start_at)
            for i in range(len(sorted_items) - 1):
                gap = (sorted_items[i + 1].start_at - sorted_items[i].end_at).total_seconds() / 3600
                if gap > 0.5:
                    n = Notification(
                        trigger_code="T1",
                        title=f"Прогноз простоя на линии {line.code}",
                        message=f"Между операциями обнаружен разрыв {gap:.1f} ч.",
                        line_id=line_id,
                        channel="in_app",
                    )
                    db.add(n)
                    created.append(n)

    db.commit()
    return created
