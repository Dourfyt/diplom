"""
Маршруты CRUD для модели Measurement.

Префикс в корневом urls.py: path('monitoring/', include(...)).
Имена: monitoring:list, monitoring:create, monitoring:update, monitoring:delete.
"""

from django.urls import path

from apps.monitoring.views import (
    MeasurementCreateView,
    MeasurementDeleteView,
    MeasurementListView,
    MeasurementUpdateView,
)

app_name = "monitoring"

urlpatterns = [
    path("measurements/", MeasurementListView.as_view(), name="list"),
    path("measurements/add/", MeasurementCreateView.as_view(), name="create"),
    path("measurements/<int:pk>/edit/", MeasurementUpdateView.as_view(), name="update"),
    path("measurements/<int:pk>/delete/", MeasurementDeleteView.as_view(), name="delete"),
]
