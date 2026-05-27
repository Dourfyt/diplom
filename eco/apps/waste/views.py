"""
Справочник видов отходов — данные с сервера GET /api/v1/core/waste-types.
"""

from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.integrations.mixins import AdminRequiredMixin, RemoteApiReadOnlyMixin
from apps.integrations.remote_data import get_remote_service
from apps.waste.forms import WasteTypeForm
from apps.waste.models import WasteType


class WasteTypeListView(AdminRequiredMixin, ListView):
    model = WasteType
    template_name = "waste/wastetype_list.html"
    context_object_name = "waste_types"
    paginate_by = 15

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        return get_remote_service().waste_types_list(search=q)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        return ctx


class WasteTypeCreateView(RemoteApiReadOnlyMixin, AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = WasteType
    form_class = WasteTypeForm
    template_name = "waste/wastetype_form.html"
    success_url = reverse_lazy("waste:list")
    success_message = "Вид отхода «%(name)s» успешно создан."

    def get_readonly_redirect_url(self):
        return reverse_lazy("waste:list")


class WasteTypeUpdateView(RemoteApiReadOnlyMixin, AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = WasteType
    form_class = WasteTypeForm
    template_name = "waste/wastetype_form.html"
    success_url = reverse_lazy("waste:list")
    success_message = "Запись «%(name)s» успешно обновлена."

    def get_readonly_redirect_url(self):
        return reverse_lazy("waste:list")


class WasteTypeDeleteView(RemoteApiReadOnlyMixin, AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    model = WasteType
    template_name = "waste/wastetype_confirm_delete.html"
    success_url = reverse_lazy("waste:list")
    success_message = "Вид отхода удалён."

    def get_readonly_redirect_url(self):
        return reverse_lazy("waste:list")
