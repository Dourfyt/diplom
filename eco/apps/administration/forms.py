from django import forms

REGISTRABLE_ROLES = (
    ("admin", "Администратор"),
    ("ecologist", "Эколог"),
    ("manager", "Руководитель"),
)


class UserRegisterForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=128,
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="Пароль",
        min_length=6,
        max_length=128,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )
    full_name = forms.CharField(
        label="ФИО",
        max_length=128,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    role = forms.ChoiceField(
        label="Роль",
        choices=REGISTRABLE_ROLES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role not in dict(REGISTRABLE_ROLES):
            raise forms.ValidationError("Недопустимая роль.")
        return role
