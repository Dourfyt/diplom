"""
Объекты-записи для шаблонов: те же атрибуты, что у моделей Django, но данные из API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any


@dataclass
class OrganizationRecord:
  pk: int
  name: str
  address: str = ""
  email: str = ""
  phone: str = ""


@dataclass
class WasteTypeRecord:
  pk: int
  code: str
  name: str
  hazard_class: int
  description: str = ""
  fkko_code: str = ""
  hazard_class_display: str = "—"


@dataclass
class BatchRecord:
  pk: int
  code: str
  name: str
  fkko_code: str
  hazard_class: int
  volume_tons: Decimal
  status: str
  status_display: str
  received_at: datetime
  organization: OrganizationRecord | None
  waste_type: WasteTypeRecord | None
  source_department: str = ""
  hazard_class_display: str = "—"


@dataclass
class ModuleRecord:
  pk: str
  name: str
  api_prefix: str
  description: str = ""


@dataclass
class MovementRecord:
  pk: int
  organization: OrganizationRecord
  waste_type: WasteTypeRecord
  operation_type: str
  operation_type_display: str
  volume: Decimal
  operation_date: date
  notes: str = ""

  def get_operation_type_display(self) -> str:
    return self.operation_type_display


@dataclass
class MeasurementRecord:
  pk: int
  organization: OrganizationRecord
  indicator_type: str
  indicator_type_display: str
  value: Decimal
  norm: Decimal | None
  measurement_date: date
  unit: str = ""

  def get_indicator_type_display(self) -> str:
    return self.indicator_type_display

  @property
  def norm_display(self) -> str:
    if self.norm is None:
      return "—"
    return str(self.norm)

  @property
  def is_exceed(self) -> bool:
    if self.norm is None:
      return False
    return self.value > self.norm
