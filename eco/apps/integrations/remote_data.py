"""
Загрузка и фильтрация данных из REST API платформы отходов.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.conf import settings

from apps.integrations.api_client import get_client
from apps.integrations.records import (
    BatchRecord,
    MeasurementRecord,
    ModuleRecord,
    MovementRecord,
    OrganizationRecord,
    WasteTypeRecord,
)

# Отображение типов операций API → учебные категории дашборда
OPERATION_TYPE_LABELS = {
    "receipt": "Поступление",
    "disposal": "Вывоз / утилизация",
    "transfer": "Передача",
    "accumulation": "Накопление",
    "recycling": "Переработка",
    "removal": "Вывоз",
}

# Для KPI и графиков: API-тип → категория объёма
OPERATION_VOLUME_GROUP = {
    "receipt": "accumulation",
    "accumulation": "accumulation",
    "transfer": "recycling",
    "recycling": "recycling",
    "disposal": "removal",
    "removal": "removal",
}

VOLUME_GROUP_LABELS = {
    "accumulation": "Поступление / накопление",
    "recycling": "Переработка / передача",
    "removal": "Вывоз / утилизация",
}

# Учебные нормативы для известных параметров (в API поля norm нет)
PARAMETER_NORMS: dict[str, Decimal] = {
    "выбросы пыли": Decimal("15"),
    "ph сточных вод": Decimal("8.5"),
}

_EMPTY_WASTE = WasteTypeRecord(pk=0, code="—", name="Не указан", hazard_class=0)


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    text = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
        return dt.date()
    except ValueError:
        return date.today()


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _org_from_dict(data: dict) -> OrganizationRecord:
    return OrganizationRecord(
        pk=int(data["id"]),
        name=data.get("name", ""),
        address=data.get("address", ""),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
    )


HAZARD_CLASS_LABELS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
}


def _waste_from_dict(data: dict) -> WasteTypeRecord:
    hazard_class = int(data.get("hazard_class", 0))
    return WasteTypeRecord(
        pk=int(data["id"]),
        code=data.get("code", ""),
        name=data.get("name", ""),
        hazard_class=hazard_class,
        description=data.get("description", ""),
        fkko_code=data.get("fkko_code", ""),
        hazard_class_display=HAZARD_CLASS_LABELS.get(
            hazard_class, str(hazard_class or "—")
        ),
    )


BATCH_STATUS_LABELS = {
    "new": "Новая",
    "classified": "Классифицирована",
    "in_storage": "На хранении",
    "in storage": "На хранении",
    "stored": "На хранении",
    "storage": "На хранении",
    "planned": "В плане",
    "in_process": "В переработке",
    "in process": "В переработке",
    "processing": "В переработке",
    "completed": "Завершена",
    "complete": "Завершена",
    "done": "Завершена",
    "disposed": "Утилизирована",
    "disposal": "Утилизирована",
    "utilized": "Утилизирована",
    "pending": "Ожидает обработки",
    "received": "Поступила",
    "active": "Активна",
    "closed": "Закрыта",
    "cancelled": "Отменена",
    "canceled": "Отменена",
    "rejected": "Отклонена",
    "archived": "В архиве",
    "draft": "Черновик",
}


def get_batch_status_display(status_key: str) -> str:
    """
    Человекочитаемый статус партии на русском.

    В БД/API хранятся технические коды на латинице (new, in_process, …).
    """
    if not status_key:
        return "—"
    raw = status_key.strip()
    normalized = raw.lower().replace("-", "_")
    spaced = normalized.replace("_", " ")
    for key in (normalized, spaced, raw.lower(), raw):
        label = BATCH_STATUS_LABELS.get(key)
        if label:
            return label
    return _humanize_unknown_batch_status(normalized)


def _humanize_unknown_batch_status(normalized: str) -> str:
    """Запасной перевод для неизвестных кодов вида in_some_status."""
    word_map = {
        "new": "новая",
        "classified": "классифицирована",
        "planned": "в плане",
        "process": "переработка",
        "processing": "переработка",
        "storage": "хранение",
        "stored": "хранение",
        "completed": "завершена",
        "complete": "завершена",
        "disposed": "утилизирована",
        "pending": "ожидает",
        "received": "поступила",
        "active": "активна",
        "closed": "закрыта",
        "cancelled": "отменена",
        "canceled": "отменена",
        "rejected": "отклонена",
        "archived": "в архиве",
        "draft": "черновик",
        "in": "",
        "on": "",
        "at": "",
    }
    parts = [word_map.get(p, p) for p in normalized.split("_") if word_map.get(p, p)]
    if parts:
        return " ".join(parts).strip().capitalize()
    return normalized.replace("_", " ").capitalize()


def _parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _in_date_range(
    item_date: date,
    date_from: date | None,
    date_to: date | None,
) -> bool:
    if date_from and item_date < date_from:
        return False
    if date_to and item_date > date_to:
        return False
    return True


class RemoteDataService:
    """Кэш справочников на время одного HTTP-запроса Django."""

    def __init__(self):
        self._client = get_client()
        self._organizations: dict[int, OrganizationRecord] | None = None
        self._waste_types: dict[int, WasteTypeRecord] | None = None

    def _load_organizations(self) -> dict[int, OrganizationRecord]:
        if self._organizations is None:
            raw = self._client.get("/api/v1/core/organizations")
            self._organizations = {
                int(item["id"]): _org_from_dict(item) for item in (raw or [])
            }
        return self._organizations

    def _load_waste_types(self) -> dict[int, WasteTypeRecord]:
        if self._waste_types is None:
            raw = self._client.get("/api/v1/core/waste-types")
            self._waste_types = {
                int(item["id"]): _waste_from_dict(item) for item in (raw or [])
            }
        return self._waste_types

    def organizations_list(self) -> list[OrganizationRecord]:
        orgs = list(self._load_organizations().values())
        orgs.sort(key=lambda o: o.name.lower())
        return orgs

    def organization_by_id(self, org_id: int | None) -> OrganizationRecord | None:
        if org_id is None:
            return None
        return self._load_organizations().get(int(org_id))

    def waste_types_list(self, *, search: str = "") -> list[WasteTypeRecord]:
        items = list(self._load_waste_types().values())
        q = search.strip().lower()
        if q:
            items = [
                w
                for w in items
                if q in w.code.lower() or q in w.name.lower()
            ]
        items.sort(key=lambda w: (w.code.lower(), w.name.lower()))
        return items

    def waste_type_by_id(self, pk: int) -> WasteTypeRecord | None:
        return self._load_waste_types().get(int(pk))

    def batches_list(
        self,
        *,
        search: str = "",
        status: str = "",
    ) -> list[BatchRecord]:
        org_map = self._load_organizations()
        waste_map = self._load_waste_types()
        raw = self._client.get("/api/v1/accounting/batches") or []

        q = search.strip().lower()
        result: list[BatchRecord] = []

        for item in raw:
            status_key = item.get("status", "")
            if status and status_key != status:
                continue

            org_id = item.get("organization_id")
            org = org_map.get(org_id) if org_id else None
            wt_id = item.get("waste_type_id")
            waste = waste_map.get(wt_id) if wt_id else None

            if q:
                hay = " ".join(
                    filter(
                        None,
                        [
                            item.get("code", ""),
                            item.get("name", ""),
                            item.get("fkko_code", ""),
                            org.name if org else "",
                            waste.name if waste else "",
                        ],
                    )
                ).lower()
                if q not in hay:
                    continue

            received_raw = item.get("received_at")
            try:
                received_at = datetime.fromisoformat(
                    (received_raw or "").replace("Z", "+00:00")
                )
            except ValueError:
                received_at = datetime.now()

            hazard_class = int(item.get("hazard_class", 0))
            result.append(
                BatchRecord(
                    pk=int(item["id"]),
                    code=item.get("code", ""),
                    name=item.get("name", ""),
                    fkko_code=item.get("fkko_code", ""),
                    hazard_class=hazard_class,
                    volume_tons=_to_decimal(item.get("volume_tons")),
                    status=status_key,
                    status_display=get_batch_status_display(status_key),
                    received_at=received_at,
                    organization=org,
                    waste_type=waste,
                    source_department=item.get("source_department") or "",
                    hazard_class_display=HAZARD_CLASS_LABELS.get(
                        hazard_class, str(hazard_class or "—")
                    ),
                )
            )

        result.sort(key=lambda b: (b.received_at, b.pk), reverse=True)
        return result

    def modules_list(self) -> list[ModuleRecord]:
        raw = self._client.get("/api/v1/core/modules") or []
        items = [
            ModuleRecord(
                pk=str(item.get("id", "")),
                name=item.get("name", ""),
                api_prefix=item.get("api_prefix", ""),
                description=item.get("description", ""),
            )
            for item in raw
        ]
        items.sort(key=lambda m: m.name.lower())
        return items

    def movements_list(
        self,
        *,
        organization_id: str | None = None,
        search: str = "",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[MovementRecord]:
        org_map = self._load_organizations()
        waste_map = self._load_waste_types()
        raw = self._client.get("/api/v1/reporting/operations") or []

        org_filter: int | None = None
        if organization_id not in (None, ""):
            try:
                org_filter = int(organization_id)
            except (TypeError, ValueError):
                org_filter = None

        q = search.strip().lower()
        result: list[MovementRecord] = []

        for item in raw:
            org_id = item.get("organization_id")
            org = org_map.get(org_id) if org_id else None
            if org is None and org_id:
                org = OrganizationRecord(pk=int(org_id), name=f"Организация #{org_id}")
            if org is None:
                org = OrganizationRecord(pk=0, name="—")

            wt_id = item.get("waste_type_id")
            waste = waste_map.get(wt_id) if wt_id else _EMPTY_WASTE

            op_type = item.get("operation_type", "")
            display = OPERATION_TYPE_LABELS.get(op_type, op_type)

            if org_filter is not None and org.pk != org_filter:
                continue

            if q:
                hay = f"{org.name} {waste.name} {waste.code}".lower()
                if q not in hay:
                    continue

            op_date = _parse_date(item.get("operation_at"))
            if not _in_date_range(op_date, date_from, date_to):
                continue

            result.append(
                MovementRecord(
                    pk=int(item["id"]),
                    organization=org,
                    waste_type=waste,
                    operation_type=op_type,
                    operation_type_display=display,
                    volume=_to_decimal(item.get("quantity_tons")),
                    operation_date=op_date,
                    notes=item.get("notes") or "",
                )
            )

        result.sort(
            key=lambda m: (m.operation_date, m.pk),
            reverse=True,
        )
        return result

    def movement_by_id(self, pk: int) -> MovementRecord | None:
        for movement in self.movements_list():
            if movement.pk == int(pk):
                return movement
        return None

    def measurements_list(
        self,
        *,
        organization_id: str | None = None,
        status: str = "",
        search: str = "",
    ) -> list[MeasurementRecord]:
        org_map = self._load_organizations()
        raw = self._client.get("/api/v1/reporting/measurements") or []

        org_filter: int | None = None
        if organization_id not in (None, ""):
            try:
                org_filter = int(organization_id)
            except (TypeError, ValueError):
                org_filter = None

        q = search.strip().lower()
        batches_map = {b.pk: b for b in self.batches_list()}
        result: list[MeasurementRecord] = []

        for item in raw:
            org_id = item.get("organization_id")
            org = org_map.get(org_id) if org_id else None
            if org is None and org_id:
                org = OrganizationRecord(pk=int(org_id), name=f"Организация #{org_id}")
            if org is None:
                org = OrganizationRecord(pk=0, name="—")

            parameter = item.get("parameter", "")
            norm = PARAMETER_NORMS.get(parameter.strip().lower())
            value = _to_decimal(item.get("value"))

            if org_filter is not None and org.pk != org_filter:
                continue

            if status == "ok" and (norm is None or value > norm):
                continue
            if status == "bad" and (norm is None or value <= norm):
                continue

            if q:
                hay = f"{org.name} {parameter}".lower()
                batch_id_raw = item.get("batch_id")
                if batch_id_raw:
                    batch = batches_map.get(int(batch_id_raw))
                    if batch:
                        hay += f" {batch.code} {batch.name}".lower()
                if q not in hay:
                    continue

            batch_id_raw = item.get("batch_id")
            batch_id = int(batch_id_raw) if batch_id_raw is not None else None
            batch_display = ""
            if batch_id is not None:
                batch = batches_map.get(batch_id)
                if batch:
                    batch_display = batch.code
                    if batch.name:
                        batch_display = f"{batch.code} — {batch.name}"
                else:
                    batch_display = f"Партия #{batch_id}"

            result.append(
                MeasurementRecord(
                    pk=int(item["id"]),
                    organization=org,
                    indicator_type=parameter,
                    indicator_type_display=parameter,
                    value=value,
                    norm=norm,
                    measurement_date=_parse_date(item.get("measured_at")),
                    unit=item.get("unit") or "",
                    batch_id=batch_id,
                    batch_display=batch_display,
                )
            )

        result.sort(
            key=lambda m: (m.measurement_date, m.pk),
            reverse=True,
        )
        return result

    def measurement_by_id(self, pk: int) -> MeasurementRecord | None:
        for row in self.measurements_list():
            if row.pk == int(pk):
                return row
        return None

    def create_measurement(
        self,
        *,
        organization_id: int,
        parameter: str,
        value: Decimal,
        unit: str,
        batch_id: int | None = None,
    ) -> dict:
        return self._client.post(
            "/api/v1/reporting/measurements",
            json_body={
                "organization_id": organization_id,
                "parameter": parameter,
                "value": float(value),
                "unit": unit,
                "batch_id": batch_id,
            },
        )

    def reporting_dashboard(self) -> dict:
        return self._client.get("/api/v1/reporting/dashboard") or {}

    def reporting_summary_by_hazard(self) -> list[dict]:
        raw = self._client.get("/api/v1/reporting/summary/by-hazard") or []
        rows: list[dict] = []
        for item in raw:
            hazard = int(item.get("hazard_class") or 0)
            rows.append(
                {
                    "hazard_class": hazard,
                    "hazard_label": HAZARD_CLASS_LABELS.get(hazard, str(hazard or "—")),
                    "batch_count": int(item.get("batch_count") or 0),
                    "volume_tons": _to_decimal(item.get("volume_tons")),
                }
            )
        rows.sort(key=lambda r: r["hazard_class"])
        return rows

    def reporting_dashboard_bundle(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        organization_id: str | None = None,
    ) -> dict:
        """
        Данные для дашборда отчётности: KPI с сервера, сводка по классам опасности,
        отфильтрованные партии и операции за период.
        """
        remote = self.reporting_dashboard()
        hazard_rows = self.reporting_summary_by_hazard()

        org_filter: int | None = None
        if organization_id not in (None, ""):
            try:
                org_filter = int(organization_id)
            except (TypeError, ValueError):
                org_filter = None

        batches = self.batches_list()
        if org_filter is not None:
            batches = [
                b
                for b in batches
                if b.organization and b.organization.pk == org_filter
            ]
        if date_from or date_to:
            batches = [
                b
                for b in batches
                if _in_date_range(b.received_at.date(), date_from, date_to)
            ]

        movements = self.movements_list(organization_id=organization_id)
        if date_from or date_to:
            movements = [
                m
                for m in movements
                if _in_date_range(m.operation_date, date_from, date_to)
            ]

        measurements = self.measurements_list(organization_id=organization_id)
        if date_from or date_to:
            measurements = [
                m
                for m in measurements
                if _in_date_range(m.measurement_date, date_from, date_to)
            ]

        batch_volume = sum((b.volume_tons for b in batches), Decimal("0"))
        op_volume = sum((m.volume for m in movements), Decimal("0"))
        exceed_count = sum(1 for m in measurements if m.is_exceed)

        chart_hazard = {
            "labels": [r["hazard_label"] for r in hazard_rows] or ["—"],
            "volumes": [float(r["volume_tons"]) for r in hazard_rows] or [0],
            "counts": [r["batch_count"] for r in hazard_rows] or [0],
        }

        op_type_counts: dict[str, int] = {}
        for m in movements:
            label = m.operation_type_display
            op_type_counts[label] = op_type_counts.get(label, 0) + 1
        if not op_type_counts:
            for label in OPERATION_TYPE_LABELS.values():
                op_type_counts.setdefault(label, 0)

        return {
            "remote": remote,
            "hazard_rows": hazard_rows,
            "chart_hazard": chart_hazard,
            "chart_operations": {
                "labels": list(op_type_counts.keys()),
                "values": list(op_type_counts.values()),
            },
            "batches": batches[:20],
            "batches_total": len(batches),
            "batch_volume": batch_volume,
            "movements": movements[:15],
            "movements_total": len(movements),
            "measurements": measurements[:15],
            "measurements_total": len(measurements),
            "operation_volume": op_volume,
            "exceed_count": exceed_count,
            "remote_organization_name": remote.get("organization_name", ""),
            "remote_total_batches": int(remote.get("total_batches") or 0),
            "remote_batches_processed": int(remote.get("batches_processed") or 0),
            "remote_total_volume": _to_decimal(remote.get("total_volume_tons")),
            "remote_avg_hazard": remote.get("avg_hazard_class"),
            "remote_plan_completion": remote.get("plan_completion_percent"),
            "remote_operations_count": int(remote.get("operations_count") or 0),
            "remote_measurements_count": int(remote.get("measurements_count") or 0),
            "line_utilization": remote.get("line_utilization") or {},
        }

    def _movements_in_period(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
    ) -> list[MovementRecord]:
        movements = self.movements_list()
        if date_from or date_to:
            movements = [
                m
                for m in movements
                if _in_date_range(m.operation_date, date_from, date_to)
            ]
        return movements

    def _measurements_in_period(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
    ) -> list[MeasurementRecord]:
        measurements = self.measurements_list()
        if date_from or date_to:
            measurements = [
                m
                for m in measurements
                if _in_date_range(m.measurement_date, date_from, date_to)
            ]
        return measurements

    def _kpi_attention_items(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
    ) -> dict:
        movements = self._movements_in_period(date_from=date_from, date_to=date_to)
        measurements = self._measurements_in_period(
            date_from=date_from, date_to=date_to
        )
        org_map = self._load_organizations()

        recent_exceedances = sorted(
            [m for m in measurements if m.is_exceed],
            key=lambda m: (m.measurement_date, m.pk),
            reverse=True,
        )[:5]

        orgs_with_ops = {m.organization.pk for m in movements}
        orgs_with_meas = {m.organization.pk for m in measurements}
        orgs_without_measurements = []
        for org_id in sorted(orgs_with_ops - orgs_with_meas):
            org = org_map.get(org_id)
            if org:
                orgs_without_measurements.append(org)
            if len(orgs_without_measurements) >= 5:
                break

        return {
            "recent_exceedances": recent_exceedances,
            "orgs_without_measurements": orgs_without_measurements,
            "exceed_count": sum(1 for m in measurements if m.is_exceed),
            "operations_count": len(movements),
            "measurements_count": len(measurements),
        }

    def dashboard_kpi_bundle(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """
        Данные для дашборда KPI: справочники, операции и измерения за период.
        """
        organizations = self.organizations_list()
        waste_types = self.waste_types_list()
        batches = self.batches_list()
        if date_from or date_to:
            batches = [
                b
                for b in batches
                if _in_date_range(b.received_at.date(), date_from, date_to)
            ]

        attention = self._kpi_attention_items(date_from=date_from, date_to=date_to)

        bundle = {
            "count_organizations": len(organizations),
            "count_waste_types": len(waste_types),
            "count_batches": len(batches),
            "total_volume": Decimal("0"),
            "accumulation_volume": Decimal("0"),
            "recycling_volume": Decimal("0"),
            "removal_volume": Decimal("0"),
            "recycling_percent": Decimal("0"),
            "exceed_count": attention["exceed_count"],
            "operations_count": attention["operations_count"],
            "measurements_count": attention["measurements_count"],
            "attention": attention,
            "date_from": date_from,
            "date_to": date_to,
        }

        try:
            charts = self.dashboard_charts(date_from=date_from, date_to=date_to)
            bundle["charts"] = charts
        except Exception:
            bundle["charts"] = None
            return bundle

        group_volumes = charts["group_volumes"]
        total_from_ops = sum(group_volumes.values(), Decimal("0"))
        recycling_dec = group_volumes.get("recycling", Decimal("0"))
        bundle["total_volume"] = total_from_ops
        bundle["accumulation_volume"] = group_volumes["accumulation"]
        bundle["recycling_volume"] = group_volumes["recycling"]
        bundle["removal_volume"] = group_volumes["removal"]
        if total_from_ops > 0:
            bundle["recycling_percent"] = recycling_dec / total_from_ops * Decimal(100)
        return bundle

    def dashboard_charts(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Данные для Chart.js на дашборде (операции за выбранный период)."""
        movements = self._movements_in_period(date_from=date_from, date_to=date_to)
        measurements = self._measurements_in_period(
            date_from=date_from, date_to=date_to
        )

        type_counts: dict[str, int] = {}
        org_volumes: dict[str, Decimal] = {}

        for m in movements:
            label = OPERATION_TYPE_LABELS.get(m.operation_type, m.operation_type)
            type_counts[label] = type_counts.get(label, 0) + 1
            org_name = m.organization.name
            org_volumes[org_name] = org_volumes.get(org_name, Decimal("0")) + m.volume

        if not type_counts:
            for label in OPERATION_TYPE_LABELS.values():
                type_counts.setdefault(label, 0)

        group_volumes = {
            "accumulation": Decimal("0"),
            "recycling": Decimal("0"),
            "removal": Decimal("0"),
        }
        for m in movements:
            group = OPERATION_VOLUME_GROUP.get(m.operation_type, "accumulation")
            group_volumes[group] = group_volumes.get(group, Decimal("0")) + m.volume

        return {
            "chart_operations": {
                "labels": list(type_counts.keys()),
                "values": list(type_counts.values()),
            },
            "chart_volume_by_org": {
                "labels": list(org_volumes.keys()) or ["—"],
                "values": [float(v) for v in org_volumes.values()] or [0],
            },
            "chart_volume_by_operation": {
                "labels": [VOLUME_GROUP_LABELS[k] for k in group_volumes],
                "values": [float(group_volumes[k]) for k in group_volumes],
            },
            "group_volumes": group_volumes,
            "exceed_count": sum(1 for m in measurements if m.is_exceed),
            "has_operations": len(movements) > 0,
        }


def get_remote_service() -> RemoteDataService:
    return RemoteDataService()


def movements_for_request(request) -> list[MovementRecord]:
    return get_remote_service().movements_list(
        organization_id=request.GET.get("organization"),
        search=request.GET.get("q", ""),
        date_from=_parse_optional_date(request.GET.get("date_from")),
        date_to=_parse_optional_date(request.GET.get("date_to")),
    )
