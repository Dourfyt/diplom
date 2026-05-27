from django.db import models

from apps.organizations.models import TimeStampedModel


class Measurement(TimeStampedModel):
    """Результат измерения показателя окружающей среды на объекте организации."""

    class IndicatorType(models.TextChoices):
        AIR = "air", "воздух"
        WASTEWATER = "wastewater", "сточные воды"
        SOIL = "soil", "почва"
        NOISE = "noise", "шум"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="measurements",
        verbose_name="организация",
    )
    indicator_type = models.CharField(
        "тип показателя",
        max_length=20,
        choices=IndicatorType.choices,
    )
    value = models.DecimalField(
        "значение",
        max_digits=12,
        decimal_places=4,
        help_text="фактическое значение измерения",
    )
    norm = models.DecimalField(
        "норматив",
        max_digits=12,
        decimal_places=4,
        help_text="предельно допустимое или нормативное значение",
    )
    measurement_date = models.DateField("дата измерения")

    class Meta:
        verbose_name = "измерение"
        verbose_name_plural = "измерения"
        ordering = ["-measurement_date", "-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.measurement_date} | {self.organization.name} | "
            f"{self.get_indicator_type_display()}"
        )
