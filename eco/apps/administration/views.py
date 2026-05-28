"""
Разделы администратора: справочники и учётные записи через REST API.
"""

from collections import defaultdict

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView

from apps.administration.forms import UserRegisterForm
from apps.integrations.auth_api import API_ROLE_LABELS, api_register
from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import AdminRequiredMixin
from apps.integrations.remote_data import BATCH_STATUS_LABELS, get_remote_service
from apps.organizations.models import Organization


class OrganizationListView(AdminRequiredMixin, ListView):
    model = Organization
    template_name = "administration/organization_list.html"
    context_object_name = "organizations"
    paginate_by = 15

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip().lower()
        items = get_remote_service().organizations_list()
        if q:
            items = [
                o
                for o in items
                if q in o.name.lower()
                or q in o.address.lower()
                or q in o.email.lower()
                or q in o.phone.lower()
            ]
        return items

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        return ctx


class BatchListView(AdminRequiredMixin, ListView):
    model = Organization
    template_name = "administration/batch_list.html"
    context_object_name = "batches"
    paginate_by = 15

    def get_queryset(self):
        return get_remote_service().batches_list(
            search=self.request.GET.get("q", ""),
            status=self.request.GET.get("status", ""),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["status_choices"] = [("", "Все статусы")] + list(
            BATCH_STATUS_LABELS.items()
        )
        batches = list(ctx.get("batches", []))
        totals = self._attach_integrity_checks(batches)
        ctx["integrity_totals"] = totals
        return ctx

    def _attach_integrity_checks(self, batches):
        service = get_remote_service()
        movements = service.movements_list()
        measurements = service.measurements_list()

        movement_count_by_org_waste = defaultdict(int)
        movement_volume_by_org_waste = defaultdict(float)
        for row in movements:
            key = (row.organization.pk, row.waste_type.pk)
            movement_count_by_org_waste[key] += 1
            movement_volume_by_org_waste[key] += float(row.volume)

        measurement_count_by_org = defaultdict(int)
        for row in measurements:
            measurement_count_by_org[row.organization.pk] += 1

        totals = {"ok": 0, "warning": 0, "problem": 0}
        for batch in batches:
            org_id = batch.organization.pk if batch.organization else 0
            waste_id = batch.waste_type.pk if batch.waste_type else 0

            ops_count = movement_count_by_org_waste[(org_id, waste_id)]
            measures_count = measurement_count_by_org[org_id]
            ops_volume = movement_volume_by_org_waste[(org_id, waste_id)]
            batch_volume = float(batch.volume_tons)

            issues = []
            if ops_count == 0:
                issues.append("нет операций по этой партии отходов")
            if measures_count == 0:
                issues.append("нет измерений по организации")
            if batch_volume > 0 and ops_volume < batch_volume * 0.5:
                issues.append("объём операций заметно ниже объёма партии")

            passed = 3 - len(issues)
            score = int((passed / 3) * 100)

            severity = "ok"
            if len(issues) >= 2:
                severity = "problem"
            elif len(issues) == 1:
                severity = "warning"
            totals[severity] += 1

            batch.integrity_check = {
                "severity": severity,
                "score": score,
                "issues": issues,
                "ops_count": ops_count,
                "measures_count": measures_count,
            }

        return totals


class ModuleListView(AdminRequiredMixin, ListView):
    model = Organization
    template_name = "administration/module_list.html"
    context_object_name = "modules"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return redirect("administration:organizations")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return get_remote_service().modules_list()


class UserRegisterView(AdminRequiredMixin, FormView):
    form_class = UserRegisterForm
    template_name = "administration/user_register.html"
    success_url = reverse_lazy("administration:user_register")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "Создание пользователей доступно только суперпользователю.")
            return redirect("administration:organizations")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            result = api_register(
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
                full_name=form.cleaned_data["full_name"],
                role=form.cleaned_data["role"],
            )
        except ApiError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        if result is None:
            form.add_error("email", "Пользователь с таким email уже существует.")
            return self.form_invalid(form)

        role_label = API_ROLE_LABELS.get(
            result.get("role", form.cleaned_data["role"]),
            form.cleaned_data["role"],
        )
        messages.success(
            self.request,
            f"Пользователь {result.get('email')} ({role_label}) создан.",
        )
        return super().form_valid(form)
