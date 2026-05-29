"""
Маршруты дашборда (главная страница после входа).
"""

from django.urls import path

from apps.dashboard.views import (
    DashboardView,
    ManagerBatchListView,
    ReportingDashboardView,
    ReportingExportExcelView,
    ReportingExportPdfView,
)

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("reporting/", ReportingDashboardView.as_view(), name="reporting"),
    path("reporting/export/excel/", ReportingExportExcelView.as_view(), name="reporting_export_excel"),
    path("reporting/export/pdf/", ReportingExportPdfView.as_view(), name="reporting_export_pdf"),
    path("batches/", ManagerBatchListView.as_view(), name="manager_batches"),
]
