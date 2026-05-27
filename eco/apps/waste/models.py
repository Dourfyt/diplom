from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.organizations.models import TimeStampedModel


class WasteType(TimeStampedModel):
    """Справочник видов промышленных отходов."""

    name = models.CharField("название отхода", max_length=255)
    code = models.CharField("код отхода", max_length=50, db_index=True)
    hazard_class = models.PositiveSmallIntegerField(
        "класс опасности",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="от 1 до 5 по классификации опасности отходов",
    )
    description = models.TextField("описание", blank=True)

    class Meta:
        verbose_name = "вид отхода"
        verbose_name_plural = "виды отходов"
        ordering = ["code", "name"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"
