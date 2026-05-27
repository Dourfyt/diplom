"""
Раньше заполнял локальную SQLite. Данные общего проекта — только на сервере API.
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Отключено: демо-данные хранятся на сервере платформы (общий проект)"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "Команда seed_demo не создаёт локальные записи.\n"
                "Все данные (партии, операции, измерения, справочники) — на сервере:\n"
                f"  {settings.API_BASE_URL}\n\n"
                "Пользователи для входа в этот модуль:\n"
                "  python manage.py setup_roles\n\n"
                "Демо-данные добавляют модули одногруппников (учёт, планирование, мониторинг) "
                "через их приложения и тот же API."
            )
        )
