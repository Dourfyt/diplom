"""
Аутентификация через REST API платформы (логин и пароль на сервере).
"""

from __future__ import annotations

from django.contrib.auth.models import Group, User

from apps.integrations.api_client import ApiClient
from apps.integrations.exceptions import ApiError
from apps.integrations.roles import (
    GROUP_ADMIN,
    GROUP_ECOLOGIST,
    GROUP_MANAGER,
    ensure_role_groups,
)

# Роль в API (PostgreSQL на сервере) → группа Django для меню и доступа
API_ROLE_TO_DJANGO_GROUP: dict[str, str] = {
    "admin": GROUP_ADMIN,
    "administrator": GROUP_ADMIN,
    "ecologist": GROUP_ECOLOGIST,
    "manager": GROUP_MANAGER,
    "chief": GROUP_MANAGER,
    "operator": GROUP_ECOLOGIST,
    "dispatcher": GROUP_ECOLOGIST,
}

# Роль в Django setup_roles → роль в API платформы
API_REGISTER_ROLE_MAP: dict[str, str] = {
    "manager": "chief",
}

API_ROLE_LABELS: dict[str, str] = {
    "admin": "Администратор",
    "administrator": "Администратор",
    "ecologist": "Эколог",
    "manager": "Руководитель",
    "chief": "Руководитель",
    "operator": "Оператор",
    "dispatcher": "Диспетчер",
}


def api_login(email: str, password: str) -> dict:
    """POST /api/v1/auth/login → access_token."""
    client = ApiClient()
    return client.post(
        "/api/v1/auth/login",
        json_body={"email": email.strip().lower(), "password": password},
    )


def api_fetch_user(access_token: str) -> dict:
    """GET /api/v1/auth/user с Bearer-токеном."""
    client = ApiClient()
    return client.get(
        "/api/v1/auth/user",
        headers_extra={"Authorization": f"Bearer {access_token}"},
    )


def api_register(
    email: str,
    password: str,
    full_name: str,
    role: str,
) -> dict | None:
    """POST /api/v1/auth/register. Если email занят — None."""
    client = ApiClient()
    api_role = API_REGISTER_ROLE_MAP.get(role, role)
    try:
        return client.post(
            "/api/v1/auth/register",
            json_body={
                "email": email.strip().lower(),
                "password": password,
                "full_name": full_name,
                "role": api_role,
            },
        )
    except ApiError as exc:
        if exc.status_code in (400, 409):
            return None
        raise


def sync_django_user_from_api(user_data: dict) -> User:
    """
    Локальный User только для сессии Django; пароль не хранится (unusable).
    Права меню — по группе, согласованной с role с сервера.
    """
    ensure_role_groups()
    email = user_data["email"].strip().lower()
    role = (user_data.get("role") or "").lower()

    user, _created = User.objects.get_or_create(
        username=email,
        defaults={"email": email},
    )
    user.email = email
    full_name = user_data.get("full_name") or ""
    if full_name:
        parts = full_name.split(maxsplit=1)
        user.first_name = parts[0][:150]
        if len(parts) > 1:
            user.last_name = parts[1][:150]
    user.is_active = bool(user_data.get("is_active", True))
    user.is_staff = role in ("admin", "administrator")
    user.set_unusable_password()
    user.save()

    user.groups.clear()
    group_name = API_ROLE_TO_DJANGO_GROUP.get(role)
    if group_name:
        user.groups.add(Group.objects.get(name=group_name))

    return user


def authenticate_with_api(email: str, password: str) -> tuple[User, str, dict]:
    """
    Проверка логина/пароля на сервере.
    Возвращает (django_user, access_token, user_data).
    """
    token_payload = api_login(email, password)
    access_token = token_payload["access_token"]
    user_data = api_fetch_user(access_token)
    django_user = sync_django_user_from_api(user_data)
    return django_user, access_token, user_data
