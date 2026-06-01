"""Единая схема БД программного комплекса (учёт · планирование · мониторинг · отчётность)."""

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ——— Пользователи (аутентификация) ———


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    full_name: Mapped[str] = mapped_column(String(128), default="")
    role: Mapped[str] = mapped_column(String(32), default="operator")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ——— Справочники (модули учёта и отчётности) ———


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    address: Mapped[str] = mapped_column(String(512), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")

    batches: Mapped[list["WasteBatch"]] = relationship(back_populates="organization")
    operations: Mapped[list["WasteOperation"]] = relationship(back_populates="organization")
    measurements: Mapped[list["EnvironmentalMeasurement"]] = relationship(
        back_populates="organization"
    )


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)


class WasteType(Base):
    __tablename__ = "waste_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    fkko_code: Mapped[str] = mapped_column(String(32), default="")
    hazard_class: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")

    batches: Mapped[list["WasteBatch"]] = relationship(back_populates="waste_type")


# ——— Планирование (Долгов) ———


class PlanStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ARCHIVED = "archived"
    PUBLISHED = "published"


class NotificationStatus(str, enum.Enum):
    NEW = "new"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"


class ProductionLine(Base):
    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    line_type: Mapped[str] = mapped_column(String(64))
    capacity_t_per_hour: Mapped[float] = mapped_column(Float, default=1.0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="line")


class WasteBatch(Base):
    """Партия отходов — общая сущность комплекса (таблица 9 диплома)."""

    __tablename__ = "waste_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    fkko_code: Mapped[str] = mapped_column(String(32))
    hazard_class: Mapped[int] = mapped_column(Integer)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    volume_unit: Mapped[str] = mapped_column(String(8), default="t")
    volume_tons: Mapped[float] = mapped_column(Float)
    storage_deadline_hours: Mapped[float] = mapped_column(Float)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="accepted")
    economic_value: Mapped[float] = mapped_column(Float, default=0.0)
    route_codes: Mapped[str] = mapped_column(String(64))
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    waste_type_id: Mapped[int | None] = mapped_column(ForeignKey("waste_types.id"), nullable=True)
    source_department: Mapped[str] = mapped_column(String(128), default="")
    qr_token: Mapped[str] = mapped_column(String(64), default="", index=True)
    classification_note: Mapped[str] = mapped_column(Text, default="")
    composition: Mapped[str] = mapped_column(Text, default="")

    organization: Mapped["Organization | None"] = relationship(back_populates="batches")
    waste_type: Mapped["WasteType | None"] = relationship(back_populates="batches")
    schedule_items: Mapped[list["ScheduleItem"]] = relationship(back_populates="batch")
    stage_progress: Mapped[list["BatchStageProgress"]] = relationship(back_populates="batch")
    deviations: Mapped[list["StageDeviation"]] = relationship(back_populates="batch")
    documents: Mapped[list["BatchDocument"]] = relationship(back_populates="batch")
    operations: Mapped[list["WasteOperation"]] = relationship(back_populates="batch")


class RoutingOperation(Base):
    __tablename__ = "routing_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    line_code: Mapped[str] = mapped_column(String(16))
    base_duration_hours: Mapped[float] = mapped_column(Float)
    output_ratio: Mapped[float] = mapped_column(Float, default=0.85)
    loss_ratio: Mapped[float] = mapped_column(Float, default=0.15)
    sequence_order: Mapped[int] = mapped_column(Integer, default=0)


class SchedulePlan(Base):
    __tablename__ = "schedule_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    horizon_hours: Mapped[float] = mapped_column(Float, default=8.0)
    status: Mapped[PlanStatus] = mapped_column(Enum(PlanStatus), default=PlanStatus.DRAFT)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    author: Mapped[str] = mapped_column(String(64), default="dispatcher")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_plan_id: Mapped[int | None] = mapped_column(ForeignKey("schedule_plans.id"), nullable=True)

    items: Mapped[list["ScheduleItem"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class ScheduleItem(Base):
    __tablename__ = "schedule_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("schedule_plans.id", ondelete="CASCADE"))
    batch_id: Mapped[int] = mapped_column(ForeignKey("waste_batches.id"))
    line_id: Mapped[int] = mapped_column(ForeignKey("production_lines.id"))
    operation_code: Mapped[str] = mapped_column(String(32))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    planned_output_tons: Mapped[float] = mapped_column(Float, default=0.0)
    planned_loss_tons: Mapped[float] = mapped_column(Float, default=0.0)

    plan: Mapped["SchedulePlan"] = relationship(back_populates="items")
    batch: Mapped["WasteBatch"] = relationship(back_populates="schedule_items")
    line: Mapped["ProductionLine"] = relationship(back_populates="schedule_items")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_code: Mapped[str] = mapped_column(String(8))
    title: Mapped[str] = mapped_column(String(256))
    message: Mapped[str] = mapped_column(Text)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("waste_batches.id"), nullable=True)
    line_id: Mapped[int | None] = mapped_column(ForeignKey("production_lines.id"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), default="in_app")
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.NEW
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_module: Mapped[str] = mapped_column(String(32), default="planning")


class LineDowntime(Base):
    __tablename__ = "line_downtimes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("production_lines.id"))
    start_at: Mapped[datetime] = mapped_column(DateTime)
    duration_hours: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(256), default="")


# ——— Мониторинг этапов (Хука) ———


class ProcessingStage(Base):
    __tablename__ = "processing_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    sequence_order: Mapped[int] = mapped_column(Integer, default=0)
    norm_hours: Mapped[float] = mapped_column(Float, default=1.0)
    line_code: Mapped[str] = mapped_column(String(16), default="")

    progress_rows: Mapped[list["BatchStageProgress"]] = relationship(back_populates="stage")


class BatchStageProgress(Base):
    __tablename__ = "batch_stage_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("waste_batches.id", ondelete="CASCADE"))
    stage_id: Mapped[int] = mapped_column(ForeignKey("processing_stages.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    planned_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    planned_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deviation_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    batch: Mapped["WasteBatch"] = relationship(back_populates="stage_progress")
    stage: Mapped["ProcessingStage"] = relationship(back_populates="progress_rows")
    events: Mapped[list["StageEvent"]] = relationship(back_populates="progress")
    deviations: Mapped[list["StageDeviation"]] = relationship(back_populates="progress")


class StageDeviation(Base):
    """Фиксация отклонения по этапу с фото (модуль мониторинга)."""

    __tablename__ = "stage_deviations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("waste_batches.id", ondelete="CASCADE"))
    progress_id: Mapped[int | None] = mapped_column(
        ForeignKey("batch_stage_progress.id", ondelete="SET NULL"), nullable=True
    )
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("processing_stages.id", ondelete="SET NULL"), nullable=True
    )
    line_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_lines.id", ondelete="SET NULL"), nullable=True
    )
    deviation_type: Mapped[str] = mapped_column(String(32), default="other")
    comment: Mapped[str] = mapped_column(Text, default="")
    operator_name: Mapped[str] = mapped_column(String(128), default="operator")
    deviation_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(128), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    batch: Mapped["WasteBatch"] = relationship(back_populates="deviations")
    progress: Mapped["BatchStageProgress | None"] = relationship(back_populates="deviations")


class StageEvent(Base):
    __tablename__ = "stage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    progress_id: Mapped[int] = mapped_column(ForeignKey("batch_stage_progress.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(64))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    operator_name: Mapped[str] = mapped_column(String(128), default="")

    progress: Mapped["BatchStageProgress"] = relationship(back_populates="events")


# ——— Учёт / документы (Корчагин) ———


class BatchDocument(Base):
    __tablename__ = "batch_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("waste_batches.id", ondelete="CASCADE"))
    document_type: Mapped[str] = mapped_column(String(32), default="confirming")
    doc_type: Mapped[str] = mapped_column(String(64), default="")
    doc_number: Mapped[str] = mapped_column(String(64), default="")
    file_name: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(128), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), default="")
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    batch: Mapped["WasteBatch"] = relationship(back_populates="documents")
    uploader: Mapped["User | None"] = relationship()


class StoredReport(Base):
    __tablename__ = "stored_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    date_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    filters_json: Mapped[str] = mapped_column(Text, default="{}")
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128), default="")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    storage_path: Mapped[str] = mapped_column(String(512))
    generated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    author: Mapped["User | None"] = relationship()


# ——— Отчётность (Журавлёва) ———


class WasteOperation(Base):
    __tablename__ = "waste_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    waste_type_id: Mapped[int | None] = mapped_column(ForeignKey("waste_types.id"), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("waste_batches.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(64))
    quantity_tons: Mapped[float] = mapped_column(Float)
    old_hazard_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_hazard_class: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operation_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, default="")

    organization: Mapped["Organization"] = relationship(back_populates="operations")
    batch: Mapped["WasteBatch | None"] = relationship(back_populates="operations")
    user: Mapped["User | None"] = relationship()


class EnvironmentalMeasurement(Base):
    __tablename__ = "environmental_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    parameter: Mapped[str] = mapped_column(String(128))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="")
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("waste_batches.id"), nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="measurements")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped["User | None"] = relationship()
