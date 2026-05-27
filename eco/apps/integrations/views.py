"""
Представления интеграции: вход через API сервера, домашняя страница.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as django_login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import RedirectView

from apps.integrations.auth_api import authenticate_with_api
from apps.integrations.exceptions import ApiError
from apps.integrations.roles import get_home_redirect_url_for_user


class ApiLoginView(View):
    """
    Вход: email и пароль проверяются на сервере (POST /api/v1/auth/login).
    В сессии сохраняется JWT для запросов к API.
    """

    template_name = "registration/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(get_home_redirect_url_for_user(request.user))
        return render(
            request,
            self.template_name,
            {"use_api_auth": True, "error_message": None, "email": ""},
        )

    def post(self, request):
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")

        if not email or not password:
            return render(
                request,
                self.template_name,
                {
                    "use_api_auth": True,
                    "error_message": "Укажите email и пароль.",
                    "email": email,
                },
            )

        try:
            user, access_token, user_data = authenticate_with_api(email, password)
        except ApiError as exc:
            return render(
                request,
                self.template_name,
                {
                    "use_api_auth": True,
                    "error_message": str(exc),
                    "email": email,
                },
            )

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["api_access_token"] = access_token
        request.session["api_user_role"] = user_data.get("role", "")
        request.session["api_user_email"] = user_data.get("email", email)

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url:
            return redirect(next_url)
        return redirect(get_home_redirect_url_for_user(user))


class ApiLogoutView(LogoutView):
    """Выход: очистка JWT в сессии."""

    def dispatch(self, request, *args, **kwargs):
        request.session.pop("api_access_token", None)
        request.session.pop("api_user_role", None)
        request.session.pop("api_user_email", None)
        return super().dispatch(request, *args, **kwargs)


class RoleLoginView(LoginView):
    """Локальный вход (если USE_API_AUTH=false)."""

    template_name = "registration/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["use_api_auth"] = False
        return ctx

    def get_success_url(self):
        return get_home_redirect_url_for_user(self.request.user)


class RoleHomeRedirectView(RedirectView):
    """Корень сайта: редирект по роли или на страницу входа."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return get_home_redirect_url_for_user(self.request.user)


def get_login_view():
    if getattr(settings, "USE_API_AUTH", False):
        return ApiLoginView.as_view()
    return RoleLoginView.as_view()


def get_logout_view():
    if getattr(settings, "USE_API_AUTH", False):
        return ApiLogoutView.as_view()
    return LogoutView.as_view()
