from django.urls import path

from apps.administration.views import (
    BatchListView,
    DataControlView,
    ModuleListView,
    OrganizationDetailView,
    OrganizationListView,
    UserRegisterView,
)

app_name = "administration"

urlpatterns = [
    path("organizations/", OrganizationListView.as_view(), name="organizations"),
    path("organizations/<int:pk>/", OrganizationDetailView.as_view(), name="organization_detail"),
    path("data-control/", DataControlView.as_view(), name="data_control"),
    path("batches/", BatchListView.as_view(), name="batches"),
    path("modules/", ModuleListView.as_view(), name="modules"),
    path("users/add/", UserRegisterView.as_view(), name="user_register"),
]
