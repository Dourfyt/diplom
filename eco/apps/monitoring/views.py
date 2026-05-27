"""
Журнал измерений — данные с сервера API (общая БД проекта).
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import DeleteView, FormView, ListView, UpdateView

from apps.integrations.exceptions import ApiError
from apps.integrations.mixins import EcologistRequiredMixin, RemoteApiReadOnlyMixin
from apps.integrations.remote_data import get_remote_service
from apps.monitoring.forms import MeasurementApiForm
from apps.monitoring.models import Measurement


class MeasurementListView(EcologistRequiredMixin, ListView):
    model = Measurement
    template_name = "monitoring/measurement_list.html"
    context_object_name = "measurements"
    paginate_by = 15

    def get_queryset(self):
        return get_remote_service().measurements_list(
            organization_id=self.request.GET.get("organization"),
            status=self.request.GET.get("status", ""),
            search=self.request.GET.get("q", ""),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["organizations"] = get_remote_service().organizations_list()
        ctx["selected_organization"] = self.request.GET.get("organization") or ""
        ctx["selected_status"] = self.request.GET.get("status") or ""
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["filter_query"] = self._build_filter_querystring()
        return ctx

    def _build_filter_querystring(self) -> str:
        params = {}
        org = self.request.GET.get("organization")
        if org not in (None, ""):
            params["organization"] = org
        status = self.request.GET.get("status")
        if status not in (None, ""):
            params["status"] = status
        q = self.request.GET.get("q", "").strip()
        if q:
            params["q"] = q
        return urlencode(params)


class MeasurementCreateView(EcologistRequiredMixin, FormView):
    """Добавление измерения на сервер (POST /api/v1/reporting/measurements)."""

    form_class = MeasurementApiForm
    template_name = "monitoring/measurement_form_api.html"
    success_url = reverse_lazy("monitoring:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        orgs = get_remote_service().organizations_list()
        kwargs["organization_choices"] = [(o.pk, o.name) for o in orgs]
        return kwargs

    def form_valid(self, form):
        try:
            get_remote_service().create_measurement(
                organization_id=int(form.cleaned_data["organization"]),
                parameter=form.cleaned_data["parameter"],
                value=form.cleaned_data["value"],
                unit=form.cleaned_data["unit"],
            )
        except ApiError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)

        messages.success(
            self.request,
            f"Измерение «{form.cleaned_data['parameter']}» сохранено на сервере.",
        )
        return redirect(self.get_success_url())


class MeasurementUpdateView(RemoteApiReadOnlyMixin, EcologistRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Measurement
    template_name = "monitoring/measurement_form.html"
    success_url = reverse_lazy("monitoring:list")
    success_message = "Измерение обновлено."

    def get_readonly_redirect_url(self):
        return reverse_lazy("monitoring:list")


class MeasurementDeleteView(RemoteApiReadOnlyMixin, EcologistRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Measurement
    template_name = "monitoring/measurement_confirm_delete.html"
    success_url = reverse_lazy("monitoring:list")
    success_message = "Запись измерения удалена."

    def get_readonly_redirect_url(self):
        return reverse_lazy("monitoring:list")
