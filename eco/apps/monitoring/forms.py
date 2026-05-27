"""
Формы для журнала измерений экологического контроля (модель Measurement).
"""

from decimal import Decimal

from django import forms

from apps.monitoring.models import Measurement


class MeasurementForm(forms.ModelForm):
    """Создание и редактирование измерения: организация, показатель, значение, норматив, дата."""

    class Meta:
        model = Measurement
        fields = (
            "organization",
            "indicator_type",
            "value",
            "norm",
            "measurement_date",
        )
        widgets = {
            "organization": forms.Select(attrs={"class": "form-select"}),
            "indicator_type": forms.Select(attrs={"class": "form-select"}),
            "value": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "norm": forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
            "measurement_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = self.fields[
            "organization"
        ].queryset.order_by("name")


class MeasurementApiForm(forms.Form):
    """Форма отправки измерения на REST API (POST /api/v1/reporting/measurements)."""

    organization = forms.ChoiceField(
        label="Организация",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    parameter = forms.CharField(
        label="Показатель",
        max_length=200,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Например: Выбросы пыли"},
        ),
    )
    value = forms.DecimalField(
        label="Значение",
        min_value=Decimal("0"),
        decimal_places=3,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "any"}),
    )
    unit = forms.CharField(
        label="Единица измерения",
        max_length=50,
        initial="мг/м³",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, organization_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = organization_choices or []
        self.fields["organization"].choices = [("", "— выберите —")] + list(choices)
