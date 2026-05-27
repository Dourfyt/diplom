from django.db import models

from apps.organizations.models import TimeStampedModel


class Movement(TimeStampedModel):
    """Движение отходов: накопление, переработка или вывоз с площадки."""

    class OperationType(models.TextChoices):
        ACCUMULATION = "accumulation", "накопление"
        RECYCLING = "recycling", "переработка"
        REMOVAL = "removal", "вывоз"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="movements",
        verbose_name="организация",
    )
    waste_type = models.ForeignKey(
        "waste.WasteType",
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="тип отхода",
    )
    operation_type = models.CharField(
        "тип операции",
        max_length=20,
        choices=OperationType.choices,
    )
    volume = models.DecimalField(
        "объём, т",
        max_digits=12,
        decimal_places=3,
        help_text="масса или объём в тоннах (учебный пример)",
    )
    operation_date = models.DateField("дата операции")

    class Meta:
        verbose_name = "движение отходов"
        verbose_name_plural = "движения отходов"
        ordering = ["-operation_date", "-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.operation_date} | {self.organization.name} | "
            f"{self.get_operation_type_display()} | {self.waste_type.code}"
        )
