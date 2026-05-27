from django.urls import path

from apps.administration.views import (
    BatchListView,
    ModuleListView,
    OrganizationListView,
    UserRegisterView,
)

app_name = "administration"

urlpatterns = [
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("batches/", BatchListView.as_view(), name="batches"),
    path("modules/", ModuleListView.as_view(), name="modules"),
    path("users/add/", UserRegisterView.as_view(), name="user_register"),
]
