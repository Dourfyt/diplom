from django.db import models


class TimeStampedModel(models.Model):
    """Общие поля даты создания и обновления записи."""

    created_at = models.DateTimeField("дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("дата обновления", auto_now=True)

    class Meta:
        abstract = True


class Organization(TimeStampedModel):
    """Предприятие или организация, ведущая учёт отходов и контроль."""

    name = models.CharField("название организации", max_length=255)
    address = models.CharField("адрес", max_length=500)
    email = models.EmailField("email")
    phone = models.CharField("телефон", max_length=30)

    class Meta:
        verbose_name = "организация"
        verbose_name_plural = "организации"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
