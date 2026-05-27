"""
Создание демо-пользователей на сервере API и синхронизация ролей в Django.

Запуск:
    python manage.py setup_roles

При USE_API_AUTH=true логин и пароль хранятся в БД сервера (POST /api/v1/auth/register).

Учётные записи (пароль для всех: eco2026):
    admin@eco.local      — администратор
    ecologist@eco.local  — эколог
    manager@eco.local    — руководитель
"""

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from apps.integrations.auth_api import (
    api_register,
    authenticate_with_api,
    sync_django_user_from_api,
)
from apps.integrations.exceptions import ApiError
from apps.integrations.roles import ensure_role_groups

DEMO_PASSWORD = "eco2026"

# email, роль на API, ФИО, is_staff в Django Admin
DEMO_USERS = (
    ("admin@eco.local", "admin", "Администратор", True),
    ("ecologist@eco.local", "ecologist", "Эколог", False),
    ("manager@eco.local", "manager", "Руководитель", False),
)


class Command(BaseCommand):
    help = "Зарегистрировать пользователей на API-сервере и настроить группы Django"

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEMO_PASSWORD,
            help=f"Пароль на сервере (по умолчанию: {DEMO_PASSWORD})",
        )
        parser.add_argument(
            "--skip-api",
            action="store_true",
            help="Только локальные группы Django, без регистрации на сервере",
        )

    def handle(self, *args, **options):
        password = options["password"]
        ensure_role_groups()
        self.stdout.write(self.style.SUCCESS("Группы Django: eco_admin, eco_ecologist, eco_manager"))

        use_api = settings.USE_API_AUTH and not options["skip_api"]

        for email, api_role, full_name, is_staff in DEMO_USERS:
            if use_api:
                try:
                    created = api_register(email, password, full_name, api_role)
                    if created:
                        self.stdout.write(f"  {email} — зарегистрирован на сервере ({api_role})")
                    else:
                        self.stdout.write(f"  {email} — уже есть на сервере, пропуск регистрации")
                    _, _, user_data = authenticate_with_api(email, password)
                    user = sync_django_user_from_api(user_data)
                except ApiError as exc:
                    self.stdout.write(self.style.ERROR(f"  {email} — ошибка API: {exc}"))
                    continue
            else:
                username = email
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={"email": email, "is_staff": is_staff, "is_active": True},
                )
                user.email = email
                user.is_staff = is_staff
                user.is_active = True
                user.set_password(password)
                user.save()
                from apps.integrations.roles import GROUP_ADMIN, GROUP_ECOLOGIST, GROUP_MANAGER

                role_to_group = {
                    "admin": GROUP_ADMIN,
                    "ecologist": GROUP_ECOLOGIST,
                    "manager": GROUP_MANAGER,
                }
                user.groups.clear()
                user.groups.add(Group.objects.get(name=role_to_group[api_role]))
                action = "создан локально" if created else "обновлён локально"
                self.stdout.write(f"  {email} — {action}")

            if not use_api:
                continue
            self.stdout.write(f"       Django: {user.username}, staff={user.is_staff}")

        self.stdout.write("")
        if use_api:
            self.stdout.write(self.style.WARNING(f"Пароль на сервере: {password}"))
            self.stdout.write("  admin@eco.local      → отходы + админка")
            self.stdout.write("  ecologist@eco.local  → операции + измерения")
            self.stdout.write("  manager@eco.local    → дашборд")
        else:
            self.stdout.write(self.style.WARNING("USE_API_AUTH=false — вход по локальной SQLite"))
