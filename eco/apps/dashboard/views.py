"""
Представления дашборда: KPI и дашборд отчётности с сервера API (общая БД проекта).
"""

from datetime import date
from decimal import Decimal
from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.dashboard.reporting_export import (
    load_reporting_bundle,
    reporting_pdf_response,
)
from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import DashboardRequiredMixin, ManagerRequiredMixin
from apps.integrations.remote_data import _parse_optional_date, get_batch_status_filter_choices, get_remote_service
from apps.integrations.roles import is_manager_only


def _format_number_display(value, max_decimals: int = 3) -> str:
    d = Decimal(value) if not isinstance(value, Decimal) else value
    quant = Decimal("1").scaleb(-max_decimals)
    text = format(d.quantize(quant), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _default_reporting_period() -> tuple[date, date]:
    today = date.today()
    return today.replace(month=1, day=1), today


def _kpi_filter_querystring(request) -> str:
    params = {}
    for key in ("date_from", "date_to"):
        value = request.GET.get(key, "").strip()
        if value:
            params[key] = value
    return urlencode(params)


def _empty_kpi_context(ctx, *, date_from: date, date_to: date):
    ctx.update(
        {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "filter_query": "",
            "count_organizations": 0,
            "count_waste_types": 0,
            "count_batches": 0,
            "total_volume": "0",
            "accumulation_volume": "0",
            "recycling_volume": "0",
            "removal_volume": "0",
            "recycling_percent": "0",
            "exceed_count": 0,
            "operations_count": 0,
            "measurements_count": 0,
            "recent_exceedances": [],
            "orgs_without_measurements": [],
        }
    )


class DashboardView(DashboardRequiredMixin, TemplateView):
    """Сводка KPI и графики с сервера за выбранный период."""

    template_name = "dashboard/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if is_manager_only(request.user):
            query = request.GET.urlencode()
            target = reverse("reporting")
            if query:
                target = f"{target}?{query}"
            return redirect(target)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        default_from, default_to = _default_reporting_period()

        date_from = _parse_optional_date(self.request.GET.get("date_from")) or default_from
        date_to = _parse_optional_date(self.request.GET.get("date_to")) or default_to
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        ctx["date_from"] = date_from.isoformat()
        ctx["date_to"] = date_to.isoformat()
        ctx["filter_query"] = _kpi_filter_querystring(self.request)
        ctx["period_label"] = (
            f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"
        )
        ctx["data_updated_at"] = timezone.localtime().strftime("%d.%m.%Y %H:%M")

        try:
            bundle = get_remote_service().dashboard_kpi_bundle(
                date_from=date_from,
                date_to=date_to,
            )
        except ApiError as exc:
            ctx["api_error"] = str(exc)
            _empty_kpi_context(ctx, date_from=date_from, date_to=date_to)
            return ctx

        ctx["count_organizations"] = bundle["count_organizations"]
        ctx["count_waste_types"] = bundle["count_waste_types"]
        ctx["count_batches"] = bundle["count_batches"]
        ctx["operations_count"] = bundle["operations_count"]
        ctx["measurements_count"] = bundle["measurements_count"]
        ctx["exceed_count"] = bundle["exceed_count"]

        attention = bundle["attention"]
        ctx["recent_exceedances"] = attention["recent_exceedances"]
        ctx["orgs_without_measurements"] = attention["orgs_without_measurements"]

        charts = bundle.get("charts")
        if charts:
            group_volumes = charts["group_volumes"]
            total_from_ops = sum(group_volumes.values(), Decimal("0"))
            recycling_dec = group_volumes.get("recycling", Decimal("0"))
            ctx["total_volume"] = _format_number_display(total_from_ops)
            ctx["accumulation_volume"] = _format_number_display(
                group_volumes["accumulation"]
            )
            ctx["recycling_volume"] = _format_number_display(group_volumes["recycling"])
            ctx["removal_volume"] = _format_number_display(group_volumes["removal"])
            if total_from_ops == 0:
                ctx["recycling_percent"] = "0"
            else:
                pct = (recycling_dec / total_from_ops * Decimal(100)).quantize(
                    Decimal("0.01")
                )
                ctx["recycling_percent"] = _format_number_display(pct, max_decimals=2)
        else:
            ctx["api_charts_warning"] = (
                "Не удалось загрузить объёмы операций. Проверьте связь с сервером."
            )
            ctx["total_volume"] = _format_number_display(bundle["total_volume"])
            ctx["accumulation_volume"] = _format_number_display(
                bundle["accumulation_volume"]
            )
            ctx["recycling_volume"] = _format_number_display(bundle["recycling_volume"])
            ctx["removal_volume"] = _format_number_display(bundle["removal_volume"])
            ctx["recycling_percent"] = _format_number_display(
                bundle["recycling_percent"], max_decimals=2
            )

        return ctx


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
            ctx["measurements"] = []
            ctx["chart_hazard"] = {"labels": [], "volumes": [], "counts": [], "classes": []}
            ctx["chart_operations"] = {"labels": [], "values": []}
            ctx["manager_insights"] = None
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
        ctx["measurements"] = bundle["measurements"]
        ctx["chart_hazard"] = bundle["chart_hazard"]
        ctx["chart_operations"] = bundle.get("chart_operations", {"labels": [], "values": []})
        ctx["manager_insights"] = None
        if is_manager_only(self.request.user):
            try:
                kpi = service.dashboard_kpi_bundle(
                    date_from=date_from,
                    date_to=date_to,
                )
                recycling = "0"
                charts = kpi.get("charts")
                if charts:
                    group = charts["group_volumes"]
                    total = sum(group.values(), Decimal("0"))
                    if total > 0:
                        recycling = _format_number_display(
                            group.get("recycling", Decimal("0")) / total * Decimal(100),
                            max_decimals=1,
                        )
                attention = kpi.get("attention", {})
                ctx["manager_insights"] = {
                    "recycling_percent": recycling,
                    "recent_exceedances": attention.get("recent_exceedances", [])[:5],
                    "orgs_without_measurements": attention.get(
                        "orgs_without_measurements", []
                    )[:5],
                }
            except ApiError:
                ctx["manager_insights"] = None
        ctx["period_label"] = (
            f"{date_from.strftime('%d.%m.%Y')} — {date_to.strftime('%d.%m.%Y')}"
        )
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


def _reporting_filter_querystring(request) -> str:
    params = {}
    for key in ("date_from", "date_to", "organization"):
        value = request.GET.get(key, "").strip()
        if value:
            params[key] = value
    return urlencode(params)


class ManagerBatchListView(ManagerRequiredMixin, ListView):
    """Просмотр партий для руководителя (без админского контроля связности)."""

    template_name = "dashboard/manager_batches.html"
    context_object_name = "batches"
    paginate_by = 15

    def get_queryset(self):
        self.api_error = None
        try:
            return get_remote_service().batches_list(
                search=self.request.GET.get("q", ""),
                status=self.request.GET.get("status", "").strip(),
            )
        except ApiError as exc:
            self.api_error = str(exc)
            return []

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["api_error"] = getattr(self, "api_error", None)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["selected_status"] = self.request.GET.get("status", "").strip()
        ctx["status_choices"] = [("", "Все статусы")] + get_batch_status_filter_choices()
        return ctx


class ReportingExportPdfView(DashboardRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            bundle, _df, _dt, period = load_reporting_bundle(request)
        except ApiError as exc:
            return HttpResponse(str(exc), status=502, content_type="text/plain; charset=utf-8")
        except FileNotFoundError as exc:
            return HttpResponse(str(exc), status=500, content_type="text/plain; charset=utf-8")
        return reporting_pdf_response(
            bundle,
            period=period,
            organization_name=bundle.get("remote_organization_name", ""),
        )
