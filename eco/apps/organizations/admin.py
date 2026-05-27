"""
Административный интерфейс: организации.

Настройки ниже делают список предприятий наглядным при демонстрации диплома:
удобный поиск, фильтры и переход по датам внесения записей.
"""

from django.contrib import admin

from apps.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Просмотр и редактирование карточек организаций."""

    # --- Список записей (таблица в админке) ---
    list_display = (
        "name",
        "address",
        "email",
        "phone",
        "created_at",
        "updated_at",
    )
    # Ссылка на редактирование с колонки «название»
    list_display_links = ("name",)
    # Сколько строк на странице (удобно листать на защите)
    list_per_page = 25

    search_fields = ("name", "address", "email", "phone")
    list_filter = ("created_at", "updated_at")
    ordering = ("name",)

    # Переход по году → месяцу → дню по дате появления записи в системе
    date_hierarchy = "created_at"

    # --- Форма одной записи ---
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "address")}),
        ("Контакты", {"fields": ("email", "phone")}),
        ("Служебная информация", {"fields": ("created_at", "updated_at")}),
    )
