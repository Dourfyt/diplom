from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models import NotificationStatus, PlanStatus


# ——— Core ———


class ModuleInfo(BaseModel):
    id: str
    name: str
    api_prefix: str
    description: str


class HealthOut(BaseModel):
    status: str
    service: str
    database: str


# ——— Auth ———


class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=128)
    role: str = Field(default="operator", max_length=32)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserAdminCreate(BaseModel):
    email: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=6, max_length=128)
    full_name: str = Field(min_length=1, max_length=128)
    role: Literal["operator", "chief", "ecologist", "admin"]


class UserAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=128)
    role: Literal["operator", "chief", "ecologist", "admin"] | None = None
    is_active: bool | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ——— Organizations / waste types ———


class OrganizationOut(BaseModel):
    id: int
    name: str
    address: str
    email: str
    phone: str

    model_config = {"from_attributes": True}


class WasteTypeOut(BaseModel):
    id: int
    code: str
    name: str
    fkko_code: str
    hazard_class: int
    description: str

    model_config = {"from_attributes": True}


class WasteTypeImportItem(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=1, max_length=256)
    fkko_code: str = Field(default="", max_length=32)
    hazard_class: int = Field(ge=0, le=5)
    description: str = Field(default="", max_length=5000)


class WasteTypeImportResult(BaseModel):
    total: int
    created: int
    updated: int


class DepartmentOut(BaseModel):
    name: str


# ——— Batches (shared) ———


class BatchOut(BaseModel):
    id: int
    code: str
    name: str
    fkko_code: str
    hazard_class: int
    volume: float | None = None
    volume_unit: str | None = None
    volume_tons: float
    storage_deadline_hours: float
    received_at: datetime
    status: str
    economic_value: float
    route_codes: str
    organization_id: int | None = None
    waste_type_id: int | None = None
    source_department: str = ""
    qr_token: str = ""
    priority_score: float | None = None
    storage_risk_hours: float | None = None
    processed_tons: float | None = None
    disposed_tons: float | None = None
    remaining_tons: float | None = None

    model_config = {"from_attributes": True}


class BatchBalanceOut(BaseModel):
    batch_id: int
    batch_code: str
    received_tons: float
    processed_tons: float
    disposed_tons: float
    remaining_tons: float


class OperationCreate(BaseModel):
    batch_id: int
    operation_type: Literal["processing", "disposal", "export", "transfer"] = Field(
        description="processing — переработка; disposal/export/transfer — вывоз/выбытие"
    )
    quantity_tons: float = Field(gt=0)
    organization_id: int | None = None
    notes: str = ""


class BatchCreate(BaseModel):
    code: str = Field(min_length=2, max_length=16)
    name: str
    fkko_code: str
    hazard_class: int = Field(ge=1, le=5)
    volume: float | None = Field(default=None, gt=0, description="Исходный объём в исходной единице")
    volume_unit: Literal["t", "kg", "m3", "l"] = "t"
    volume_tons: float = Field(gt=0)
    storage_deadline_hours: float = Field(gt=0)
    route_codes: str = "L1,L2"
    economic_value: float = 0
    organization_id: int | None = None
    waste_type_id: int | None = None
    source_department: str = ""
    classification_note: str = ""


class BatchClassify(BaseModel):
    hazard_class: int = Field(ge=1, le=5)
    fkko_code: str | None = None
    classification_note: str = ""
    route_codes: str | None = None


class BatchReject(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


# ——— Planning ———


class LineOut(BaseModel):
    id: int
    code: str
    name: str
    line_type: str
    capacity_t_per_hour: float
    is_available: bool

    model_config = {"from_attributes": True}


class ScheduleItemOut(BaseModel):
    id: int
    plan_id: int
    batch_id: int
    batch_code: str
    line_id: int
    line_code: str
    operation_code: str
    start_at: datetime
    end_at: datetime
    priority_score: float
    planned_output_tons: float
    planned_loss_tons: float

    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    id: int
    name: str
    horizon_hours: float
    status: PlanStatus
    status_label: str
    version_no: int
    author: str
    created_at: datetime
    approved_at: datetime | None
    is_simulation: bool
    parent_plan_id: int | None
    items: list[ScheduleItemOut] = []

    model_config = {"from_attributes": True}


class PlanActionResult(BaseModel):
    plan: PlanOut
    message: str


class BuildPlanRequest(BaseModel):
    name: str = "Сменный план"
    horizon_hours: float = Field(default=8.0, ge=1, le=168)
    batch_ids: list[int] | None = None


class SimulationRequest(BaseModel):
    base_plan_id: int
    name: str = "Симуляция"
    scenario: str = Field(default="baseline", pattern="^(baseline|accelerated|emergency)$")
    line_downtime: dict[str, float] | None = None


class DowntimeRequest(BaseModel):
    line_code: str
    duration_hours: float = Field(ge=0.5, le=72)
    reason: str = "Аварийная остановка"


class NotificationOut(BaseModel):
    id: int
    trigger_code: str
    title: str
    message: str
    batch_id: int | None
    line_id: int | None
    channel: str
    status: NotificationStatus
    created_at: datetime
    source_module: str = "planning"

    model_config = {"from_attributes": True}


class KpiDashboard(BaseModel):
    plan_id: int | None
    total_batches: int
    scheduled_batches: int
    line_utilization: dict[str, float]
    total_idle_hours: float
    batches_at_storage_risk: int
    avg_priority: float
    notifications_new: int
    oee_percent: float
    plan_completion_percent: float


class SimulationCompare(BaseModel):
    base_plan_id: int
    sim_plan_id: int
    kpi_base: KpiDashboard
    kpi_sim: KpiDashboard
    differences: dict[str, float]


# ——— Monitoring ———


class StageOut(BaseModel):
    id: int
    code: str
    name: str
    sequence_order: int
    norm_hours: float
    line_code: str

    model_config = {"from_attributes": True}


class StageProgressOut(BaseModel):
    id: int
    batch_id: int
    batch_code: str
    stage_id: int
    stage_code: str
    stage_name: str
    status: str
    status_label: str
    planned_start: datetime | None
    planned_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    deviation_percent: float | None


class StageEventCreate(BaseModel):
    event_type: str
    comment: str = ""
    operator_name: str = "operator"


class StageStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|in_progress|done|delayed)$")
    quantity_tons: float | None = Field(
        default=None,
        gt=0,
        description="Факт переработки, т (при status=done; иначе — из плана)",
    )
    record_processing: bool = Field(
        default=True,
        description="При status=done записать операцию processing в журнал учёта",
    )


class MonitoringBatchOut(BaseModel):
    batch: BatchOut
    stages: list[StageProgressOut]


# ——— Reporting ———


class WasteOperationOut(BaseModel):
    id: int
    organization_id: int
    waste_type_id: int | None
    batch_id: int | None
    operation_type: str
    quantity_tons: float
    user_id: int | None = None
    user_name: str | None = None
    old_hazard_class: int | None = None
    new_hazard_class: int | None = None
    operation_at: datetime
    notes: str

    model_config = {"from_attributes": True}


class MeasurementCreate(BaseModel):
    organization_id: int
    parameter: str
    value: float
    unit: str = ""
    batch_id: int | None = None


class MeasurementOut(BaseModel):
    id: int
    organization_id: int
    parameter: str
    value: float
    unit: str
    measured_at: datetime
    batch_id: int | None

    model_config = {"from_attributes": True}


class ReportingDashboard(BaseModel):
    organization_name: str
    total_batches: int
    batches_processed: int
    total_volume_tons: float
    total_processed_tons: float
    total_disposed_tons: float
    total_remaining_tons: float
    avg_hazard_class: float
    line_utilization: dict[str, float]
    plan_completion_percent: float
    measurements_count: int
    operations_count: int


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    user_name: str | None = None
    action: str
    entity_type: str
    entity_id: int | None
    details: str
    created_at: datetime

    model_config = {"from_attributes": True}
