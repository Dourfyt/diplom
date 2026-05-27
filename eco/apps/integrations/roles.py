"""
Роли пользователей (табл. 2.1 диплома): группы Django и проверка доступа.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, User
from django.urls import reverse

# Имена групп в БД (латиница — требование Django)
GROUP_ADMIN = "eco_admin"
GROUP_ECOLOGIST = "eco_ecologist"
GROUP_MANAGER = "eco_manager"

GROUP_LABELS = {
    GROUP_ADMIN: "Администратор",
    GROUP_ECOLOGIST: "Эколог",
    GROUP_MANAGER: "Руководитель",
}

GROUP_DESCRIPTIONS = {
    GROUP_ADMIN: "Настройка справочников, работа в Django Admin",
    GROUP_ECOLOGIST: "Операции, измерения, дашборд, экспорт отчётов",
    GROUP_MANAGER: "Дашборд и KPI",
}


def user_has_any_group(user: User, *group_names: str) -> bool:
    """Суперпользователь имеет доступ ко всем разделам."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if not group_names:
        return False
    return user.groups.filter(name__in=group_names).exists()


def is_admin(user: User) -> bool:
    return user_has_any_group(user, GROUP_ADMIN)


def is_ecologist(user: User) -> bool:
    return user_has_any_group(user, GROUP_ECOLOGIST)


def is_manager(user: User) -> bool:
    return user_has_any_group(user, GROUP_MANAGER)


def can_access_dashboard(user: User) -> bool:
    return user_has_any_group(user, GROUP_ECOLOGIST, GROUP_MANAGER)


def get_user_role_label(user: User) -> str:
    if not user.is_authenticated:
        return ""
    if user.is_superuser:
        return "Суперпользователь"
    names = list(user.groups.filter(name__in=GROUP_LABELS).values_list("name", flat=True))
    if not names:
        return "Без роли"
    # При нескольких группах показываем все через запятую
    return ", ".join(GROUP_LABELS.get(n, n) for n in sorted(names))


def get_home_url_name_for_user(user: User) -> str:
    """Имя маршрута для редиректа после входа / при отказе в доступе."""
    if not user.is_authenticated:
        return "login"
    if user.is_superuser or is_admin(user):
        return "administration:organizations"
    if is_ecologist(user):
        return "dashboard"
    if is_manager(user):
        return "dashboard"
    return "login"


def get_home_redirect_url_for_user(user: User) -> str:
    return reverse(get_home_url_name_for_user(user))


def ensure_role_groups() -> dict[str, Group]:
    """Создаёт три группы ролей, если их ещё нет."""
    groups = {}
    for name, label in GROUP_LABELS.items():
        group, _ = Group.objects.get_or_create(name=name)
        groups[name] = group
    return groups
