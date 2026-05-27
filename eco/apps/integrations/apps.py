from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.integrations"
    verbose_name = "Интеграция с REST API"

    def ready(self):
        from django.conf import settings

        if not getattr(settings, "USE_REMOTE_API", True):
            return

        self._unregister_business_admin()
        self._patch_admin_site_header()

    def _unregister_business_admin(self):
        """Бизнес-данные только на сервере — не дублируем в локальной SQLite через админку."""
        from django.contrib import admin

        from apps.monitoring.models import Measurement
        from apps.operations.models import Movement
        from apps.organizations.models import Organization
        from apps.waste.models import WasteType

        for model in (Organization, WasteType, Movement, Measurement):
            try:
                admin.site.unregister(model)
            except admin.sites.NotRegistered:
                pass

    def _patch_admin_site_header(self):
        from django.conf import settings
        from django.contrib import admin

        admin.site.site_header = "Эко-учёт (только служебные записи Django)"
        admin.site.site_title = "Эко-учёт"
        admin.site.index_title = (
            "Локальная база не содержит отходов и операций. "
            f"Данные общего проекта: {settings.API_BASE_URL}"
        )
