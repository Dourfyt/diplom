"""
Разделы администратора: справочники и учётные записи через REST API.
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView

from apps.administration.data_quality import (
    attach_batch_integrity_checks,
    compute_organization_summary,
    load_cross_module_indexes,
    organization_matches_filter,
    SEVERITY_RANK,
)
from apps.administration.forms import UserRegisterForm
from apps.integrations.auth_api import API_ROLE_LABELS, api_register
from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import AdminRequiredMixin
from apps.integrations.remote_data import get_batch_status_filter_choices, get_remote_service
from apps.organizations.models import Organization

ORGANIZATION_FILTER_CHOICES = [
    ("", "Все организации"),
    ("problems", "С замечаниями"),
    ("no_batches", "Без партий"),
    ("no_measurements", "Без измерений"),
    ("incomplete_requisites", "Неполные реквизиты"),
]


class OrganizationListView(AdminRequiredMixin, ListView):
    model = Organization
    template_name = "administration/organization_list.html"
    context_object_name = "organizations"
    paginate_by = 15

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip().lower()
        filter_key = self.request.GET.get("filter", "").strip()

        service = get_remote_service()
        indexes = load_cross_module_indexes(service)

        items = service.organizations_list()
        result = []
        for org in items:
            summary = compute_organization_summary(org, indexes)
            org.data_summary = summary
            if not organization_matches_filter(summary, filter_key):
                continue
            if q:
                hay = " ".join(
                    [org.name, org.address, org.email, org.phone]
                ).lower()
                if q not in hay:
                    continue
            result.append(org)

        result.sort(
            key=lambda o: (
                -SEVERITY_RANK[o.data_summary["severity"]],
                o.name.lower(),
            )
        )
        totals = {"ok": 0, "warning": 0, "problem": 0}
        for org in result:
            totals[org.data_summary["severity"]] += 1
        self._org_integrity_totals = totals
        return result

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["selected_filter"] = self.request.GET.get("filter", "").strip()
        ctx["filter_choices"] = ORGANIZATION_FILTER_CHOICES
        ctx["org_integrity_totals"] = getattr(
            self,
            "_org_integrity_totals",
            {"ok": 0, "warning": 0, "problem": 0},
        )
        return ctx


class OrganizationDetailView(AdminRequiredMixin, TemplateView):
    template_name = "administration/organization_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        pk = int(kwargs["pk"])
        service = get_remote_service()
        org = service.organization_by_id(pk)
        if org is None:
            raise Http404

        indexes = load_cross_module_indexes(service)
        summary = compute_organization_summary(org, indexes)
        batches = sorted(
            indexes["batches_by_org"][pk],
            key=lambda b: (b.received_at, b.pk),
            reverse=True,
        )
        recent_movements = [
            m
            for m in indexes["movements"]
            if m.organization.pk == pk
        ][:10]
        recent_measurements = [
            m
            for m in indexes["measurements"]
            if m.organization.pk == pk
        ][:10]

        ctx.update(
            {
                "organization": org,
                "summary": summary,
                "batches": batches,
                "recent_movements": recent_movements,
                "recent_measurements": recent_measurements,
            }
        )
        return ctx


class DataControlView(AdminRequiredMixin, TemplateView):
    template_name = "administration/data_control.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        service = get_remote_service()
        indexes = load_cross_module_indexes(service)

        org_totals = {"ok": 0, "warning": 0, "problem": 0}
        problematic = []
        for org in service.organizations_list():
            summary = compute_organization_summary(org, indexes)
            org.data_summary = summary
            org_totals[summary["severity"]] += 1
            if summary["severity"] != "ok":
                problematic.append(org)

        problematic.sort(
            key=lambda o: (
                -SEVERITY_RANK[o.data_summary["severity"]],
                o.name.lower(),
            )
        )

        batch_totals = attach_batch_integrity_checks(indexes["batches"], indexes)

        ctx["org_totals"] = org_totals
        ctx["batch_totals"] = batch_totals
        ctx["problematic_organizations"] = problematic
        ctx["stats"] = {
            "org_total": sum(org_totals.values()),
            "org_with_issues": org_totals["warning"] + org_totals["problem"],
            "batch_total": len(indexes["batches"]),
            "batch_problems": batch_totals["problem"] + batch_totals["warning"],
        }
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
        ctx["status_choices"] = [("", "Все статусы")] + get_batch_status_filter_choices()
        batches = list(ctx.get("batches", []))
        indexes = load_cross_module_indexes(get_remote_service())
        ctx["integrity_totals"] = attach_batch_integrity_checks(batches, indexes)
        return ctx


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
