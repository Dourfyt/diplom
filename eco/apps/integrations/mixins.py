"""
Миксины для представлений: REST API и роли пользователей.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

from apps.integrations.roles import (
    GROUP_ADMIN,
    GROUP_ECOLOGIST,
    GROUP_MANAGER,
    get_home_redirect_url_for_user,
    user_has_any_group,
)


class RemoteApiReadOnlyMixin:
    """Блокирует создание/изменение/удаление — данные только из API."""

    remote_readonly_message = (
        "Изменение недоступно: данные загружаются с сервера платформы отходов."
    )

    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings

        if settings.USE_REMOTE_API:
            messages.warning(request, self.remote_readonly_message)
            return redirect(self.get_readonly_redirect_url())
        return super().dispatch(request, *args, **kwargs)

    def get_readonly_redirect_url(self):
        raise NotImplementedError


class GroupRequiredMixin(LoginRequiredMixin):
    """Доступ только для пользователей из указанных групп (или суперпользователя)."""

    required_groups: tuple[str, ...] = ()
    access_denied_message = "Недостаточно прав для этого раздела."

    def has_role_access(self) -> bool:
        return user_has_any_group(self.request.user, *self.required_groups)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.has_role_access():
            messages.error(request, self.access_denied_message)
            return redirect(get_home_redirect_url_for_user(request.user))
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(GroupRequiredMixin):
    required_groups = (GROUP_ADMIN,)
    access_denied_message = "Раздел доступен только администратору."


class EcologistRequiredMixin(GroupRequiredMixin):
    required_groups = (GROUP_ECOLOGIST,)
    access_denied_message = "Раздел доступен только экологу."


class EcologistOrManagerRequiredMixin(GroupRequiredMixin):
    """Журналы и просмотр данных — эколог (с правкой) и руководитель (только чтение)."""

    required_groups = (GROUP_ECOLOGIST, GROUP_MANAGER)
    access_denied_message = "Раздел доступен экологу и руководителю."


class ManagerRequiredMixin(GroupRequiredMixin):
    required_groups = (GROUP_MANAGER,)
    access_denied_message = "Раздел доступен только руководителю."


class DashboardRequiredMixin(GroupRequiredMixin):
    required_groups = (GROUP_ECOLOGIST, GROUP_MANAGER)
    access_denied_message = "Дашборд доступен экологу и руководителю."
