"""
Административный интерфейс: движения отходов.

Журнал операций с фильтрами и иерархией по дате операции — наглядная
демонстрация учёта накопления, переработки и вывоза.
"""

from django.contrib import admin

from apps.operations.models import Movement


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    """Журнал операций с отходами."""

    list_display = (
        "operation_date",
        "organization",
        "waste_type",
        "operation_type",
        "volume",
        "created_at",
        "updated_at",
    )
    list_display_links = ("operation_date",)
    list_per_page = 25

    search_fields = (
        "organization__name",
        "waste_type__code",
        "waste_type__name",
    )
    list_filter = (
        "operation_type",
        "operation_date",
        "organization",
        "waste_type",
    )
    ordering = ("-operation_date", "-created_at")
    date_hierarchy = "operation_date"

    # Меньше запросов к БД при отрисовке списка (связанные объекты подгружаются сразу)
    list_select_related = ("organization", "waste_type")

    autocomplete_fields = ("organization", "waste_type")

    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("organization", "waste_type", "operation_type")}),
        ("Объём и дата", {"fields": ("volume", "operation_date")}),
        ("Служебная информация", {"fields": ("created_at", "updated_at")}),
    )
