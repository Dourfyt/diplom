"""
Административный интерфейс: справочник видов отходов.

Фильтр по классу опасности позволяет быстро показать на защите группировку
отходов по степени опасности.
"""

from django.contrib import admin

from apps.waste.models import WasteType


@admin.register(WasteType)
class WasteTypeAdmin(admin.ModelAdmin):
    """Просмотр и редактирование видов отходов."""

    list_display = (
        "code",
        "name",
        "hazard_class",
        "created_at",
        "updated_at",
    )
    list_display_links = ("code", "name")
    list_per_page = 25

    search_fields = ("code", "name", "description")
    list_filter = ("hazard_class", "created_at", "updated_at")
    ordering = ("code", "name")

    date_hierarchy = "created_at"

    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("code", "name", "hazard_class")}),
        ("Описание", {"fields": ("description",)}),
        ("Служебная информация", {"fields": ("created_at", "updated_at")}),
    )
