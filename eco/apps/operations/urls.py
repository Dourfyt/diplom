"""
Маршруты CRUD для модели Movement.

Префикс в корневом urls.py: path('operations/', include(...)).
Имена: operations:list, operations:create, operations:update, operations:delete.
"""

from django.urls import path

from apps.operations.views import (
    MovementCreateView,
    MovementDeleteView,
    MovementExportExcelView,
    MovementExportPdfView,
    MovementExportXmlView,
    MovementListView,
    MovementUpdateView,
)

app_name = "operations"

urlpatterns = [
    path("movements/", MovementListView.as_view(), name="list"),
    path("movements/export/excel/", MovementExportExcelView.as_view(), name="export_excel"),
    path("movements/export/pdf/", MovementExportPdfView.as_view(), name="export_pdf"),
    path("movements/export/xml/", MovementExportXmlView.as_view(), name="export_xml"),
    path("movements/add/", MovementCreateView.as_view(), name="create"),
    path("movements/<int:pk>/edit/", MovementUpdateView.as_view(), name="update"),
    path("movements/<int:pk>/delete/", MovementDeleteView.as_view(), name="delete"),
]
