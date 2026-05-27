"""
Маршруты CRUD для модели WasteType.

Префикс задаётся в корневом urls.py (например path('waste/', include(...))).
Имена маршрутов: waste:list, waste:create, waste:update, waste:delete.
"""

from django.urls import path

from apps.waste.views import (
    WasteTypeCreateView,
    WasteTypeDeleteView,
    WasteTypeListView,
    WasteTypeUpdateView,
)

app_name = "waste"

urlpatterns = [
    path("types/", WasteTypeListView.as_view(), name="list"),
    path("types/add/", WasteTypeCreateView.as_view(), name="create"),
    path("types/<int:pk>/edit/", WasteTypeUpdateView.as_view(), name="update"),
    path("types/<int:pk>/delete/", WasteTypeDeleteView.as_view(), name="delete"),
]
