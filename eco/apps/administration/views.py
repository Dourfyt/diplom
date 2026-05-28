"""
Разделы администратора: справочники и учётные записи через REST API.
"""

from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect
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
        return ctx


class ModuleListView(AdminRequiredMixin, ListView):
    model = Organization
    template_name = "administration/module_list.html"
    context_object_name = "modules"
    paginate_by = 20

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
