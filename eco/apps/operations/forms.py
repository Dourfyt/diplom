"""
Формы для журнала движений отходов (модель Movement).
"""

from django import forms

from apps.operations.models import Movement


class MovementForm(forms.ModelForm):
    """Создание и редактирование операции: организация, вид отхода, тип, объём, дата."""

    class Meta:
        model = Movement
        fields = (
            "organization",
            "waste_type",
            "operation_type",
            "volume",
            "operation_date",
        )
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "waste_type": forms.Select(attrs={"class": "form-select"}),
            "operation_type": forms.Select(attrs={"class": "form-select"}),
            "volume": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.001", "min": "0"}
            ),
            "operation_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Удобные подписи в выпадающих списках (для дипломной демонстрации)
        self.fields["organization"].queryset = self.fields[
            "organization"
        ].queryset.order_by("name")
        self.fields["waste_type"].queryset = self.fields["waste_type"].queryset.order_by(
            "code", "name"
        )
