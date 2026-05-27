"""
Представления дашборда: KPI и дашборд отчётности с сервера API (общая БД проекта).
"""

from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from django.views.generic import TemplateView

from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import DashboardRequiredMixin
from apps.integrations.remote_data import _parse_optional_date, get_remote_service


def _format_number_display(value, max_decimals: int = 3) -> str:
    d = Decimal(value) if not isinstance(value, Decimal) else value
    quant = Decimal("1").scaleb(-max_decimals)
    text = format(d.quantize(quant), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class DashboardView(DashboardRequiredMixin, TemplateView):
    """Сводка KPI и графики с сервера."""

    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        try:
            bundle = get_remote_service().dashboard_kpi_bundle()
        except ApiError as exc:
            ctx["api_error"] = str(exc)
            ctx["count_organizations"] = 0
            ctx["count_waste_types"] = 0
            ctx["total_volume"] = "0"
            ctx["accumulation_volume"] = "0"
            ctx["recycling_volume"] = "0"
            ctx["removal_volume"] = "0"
            ctx["recycling_percent"] = "0"
            ctx["exceed_count"] = 0
            ctx["count_exceed_measurements"] = 0
            ctx["chart_operations"] = {"labels": [], "values": []}
            ctx["chart_volume_by_org"] = {"labels": [], "values": []}
            ctx["chart_volume_by_operation"] = {"labels": [], "values": []}
            return ctx

        total_dec = bundle["total_volume"]
        ctx["count_organizations"] = bundle["count_organizations"]
        ctx["count_waste_types"] = bundle["count_waste_types"]
        ctx["total_volume"] = _format_number_display(total_dec)
        ctx["remote_organization_name"] = bundle.get("remote_organization_name", "")
        ctx["remote_total_batches"] = bundle.get("remote_total_batches", 0)

        charts = bundle.get("charts")
        if charts:
            group_volumes = charts["group_volumes"]
            total_from_ops = sum(group_volumes.values(), Decimal("0"))
            recycling_dec = group_volumes.get("recycling", Decimal("0"))
            ctx["accumulation_volume"] = _format_number_display(group_volumes["accumulation"])
            ctx["recycling_volume"] = _format_number_display(group_volumes["recycling"])
            ctx["removal_volume"] = _format_number_display(group_volumes["removal"])
            if total_from_ops == 0:
                ctx["recycling_percent"] = "0"
            else:
                pct = (recycling_dec / total_from_ops * Decimal(100)).quantize(Decimal("0.01"))
                ctx["recycling_percent"] = _format_number_display(pct, max_decimals=2)
            ctx["exceed_count"] = charts["exceed_count"]
            ctx["count_exceed_measurements"] = charts["exceed_count"]
            ctx["chart_operations"] = charts["chart_operations"]
            ctx["chart_volume_by_org"] = charts["chart_volume_by_org"]
            ctx["chart_volume_by_operation"] = charts["chart_volume_by_operation"]
        else:
            ctx["api_charts_warning"] = (
                "Графики временно недоступны. Основные показатели загружены с отчётного дашборда сервера."
            )
            ctx["accumulation_volume"] = _format_number_display(total_dec)
            ctx["recycling_volume"] = "0"
            ctx["removal_volume"] = "0"
            ctx["recycling_percent"] = "0"
            ctx["exceed_count"] = 0
            ctx["count_exceed_measurements"] = 0
            ctx["chart_operations"] = {"labels": [], "values": []}
            ctx["chart_volume_by_org"] = {"labels": [], "values": []}
            ctx["chart_volume_by_operation"] = {"labels": [], "values": []}

        return ctx


def _default_reporting_period() -> tuple[date, date]:
    today = date.today()
    return today.replace(month=1, day=1), today


def _reporting_filter_querystring(request) -> str:
    params = {}
    for key in ("date_from", "date_to", "organization"):
        value = request.GET.get(key, "").strip()
        if value:
            params[key] = value
    return urlencode(params)


class ReportingDashboardView(DashboardRequiredMixin, TemplateView):
    """Дашборд отчётности: KPI, сводка по классам опасности, таблицы за период."""

    template_name = "dashboard/reporting.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        default_from, default_to = _default_reporting_period()

        date_from = _parse_optional_date(self.request.GET.get("date_from")) or default_from
        date_to = _parse_optional_date(self.request.GET.get("date_to")) or default_to
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        organization_id = self.request.GET.get("organization", "").strip()
        ctx["date_from"] = date_from.isoformat()
        ctx["date_to"] = date_to.isoformat()
        ctx["selected_organization"] = organization_id
        ctx["filter_query"] = _reporting_filter_querystring(self.request)
        try:
            service = get_remote_service()
            ctx["organizations"] = service.organizations_list()
            bundle = service.reporting_dashboard_bundle(
                date_from=date_from,
                date_to=date_to,
                organization_id=organization_id or None,
            )
        except ApiError as exc:
            ctx["api_error"] = str(exc)
            ctx["organizations"] = []
            ctx["hazard_rows"] = []
            ctx["batches"] = []
            ctx["movements"] = []
            ctx["chart_hazard"] = {"labels": [], "volumes": [], "counts": []}
            ctx["chart_operations"] = {"labels": [], "values": []}
            ctx["batches_total"] = 0
            ctx["batch_volume"] = "0"
            ctx["movements_total"] = 0
            ctx["operation_volume"] = "0"
            ctx["measurements_total"] = 0
            ctx["exceed_count"] = 0
            ctx["remote_organization_name"] = ""
            ctx["remote_total_batches"] = 0
            ctx["remote_batches_processed"] = 0
            ctx["remote_total_volume"] = "0"
            ctx["remote_avg_hazard"] = "—"
            ctx["remote_plan_completion"] = "—"
            ctx["remote_operations_count"] = 0
            ctx["remote_measurements_count"] = 0
            ctx["line_utilization"] = {}
            return ctx

        ctx["hazard_rows"] = bundle["hazard_rows"]
        ctx["batches"] = bundle["batches"]
        ctx["movements"] = bundle["movements"]
        ctx["chart_hazard"] = bundle["chart_hazard"]
        ctx["chart_operations"] = bundle["chart_operations"]
        ctx["batches_total"] = bundle["batches_total"]
        ctx["batch_volume"] = _format_number_display(bundle["batch_volume"])
        ctx["movements_total"] = bundle["movements_total"]
        ctx["operation_volume"] = _format_number_display(bundle["operation_volume"])
        ctx["measurements_total"] = bundle["measurements_total"]
        ctx["exceed_count"] = bundle["exceed_count"]
        ctx["remote_organization_name"] = bundle["remote_organization_name"]
        ctx["remote_total_batches"] = bundle["remote_total_batches"]
        ctx["remote_batches_processed"] = bundle["remote_batches_processed"]
        ctx["remote_total_volume"] = _format_number_display(bundle["remote_total_volume"])
        avg_hazard = bundle.get("remote_avg_hazard")
        ctx["remote_avg_hazard"] = (
            _format_number_display(Decimal(str(avg_hazard)), max_decimals=1)
            if avg_hazard is not None
            else "—"
        )
        plan = bundle.get("remote_plan_completion")
        ctx["remote_plan_completion"] = (
            _format_number_display(Decimal(str(plan)), max_decimals=1)
            if plan is not None
            else "—"
        )
        ctx["remote_operations_count"] = bundle["remote_operations_count"]
        ctx["remote_measurements_count"] = bundle["remote_measurements_count"]
        ctx["line_utilization"] = bundle["line_utilization"]
        return ctx
