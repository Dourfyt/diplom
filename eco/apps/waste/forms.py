"""
Формы для работы с видами отходов в пользовательском интерфейсе (не в админке).
"""

from django import forms

from apps.waste.models import WasteType


class WasteTypeForm(forms.ModelForm):
    """Форма создания и редактирования WasteType с классами Bootstrap."""

    class Meta:
        model = WasteType
        fields = ("code", "name", "hazard_class", "description")
        widgets = {
            "code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Например, код по классификатору"}
            ),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "hazard_class": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "max": 5, "step": 1}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Необязательно"}
            ),
        }
