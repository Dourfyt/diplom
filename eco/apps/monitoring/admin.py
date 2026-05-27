"""
Административный интерфейс: измерения экологического контроля.

Дополнительная колонка «в пределах норматива» наглядно показывает
соответствие факта норме без отдельных отчётов.
"""

from django.contrib import admin

from apps.monitoring.models import Measurement


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    """Журнал измерений показателей."""

    list_display = (
        "measurement_date",
        "organization",
        "indicator_type",
        "value",
        "norm",
        "is_within_norm",
        "created_at",
        "updated_at",
    )
    list_display_links = ("measurement_date",)
    list_per_page = 25

    search_fields = ("organization__name",)
    list_filter = (
        "indicator_type",
        "measurement_date",
        "organization",
    )
    ordering = ("-measurement_date", "-created_at")
    date_hierarchy = "measurement_date"

    list_select_related = ("organization",)

    autocomplete_fields = ("organization",)

    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("organization", "indicator_type")}),
        ("Результат измерения", {"fields": ("value", "norm", "measurement_date")}),
        ("Служебная информация", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="в пределах норматива", boolean=True)
    def is_within_norm(self, obj: Measurement) -> bool:
        """True, если факт не превышает норматив (учебное упрощение без единиц)."""
        return obj.value <= obj.norm
