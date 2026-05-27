"""
Маршруты дашборда (главная страница после входа).
"""

from django.urls import path

from apps.dashboard.views import DashboardView, ReportingDashboardView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("reporting/", ReportingDashboardView.as_view(), name="reporting"),
]
