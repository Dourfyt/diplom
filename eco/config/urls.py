"""
Корневые URL проекта: админка, вход/выход, дашборд.
"""

from django.contrib import admin
from django.urls import include, path

from apps.integrations.views import (
    RoleHomeRedirectView,
    get_login_view,
    get_logout_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', get_login_view(), name='login'),
    path('accounts/logout/', get_logout_view(), name='logout'),
    path('dashboard/', include('apps.dashboard.urls')),
    path('manage/', include('apps.administration.urls')),
    path('waste/', include('apps.waste.urls')),
    path('operations/', include('apps.operations.urls')),
    path('monitoring/', include('apps.monitoring.urls')),
    path('', RoleHomeRedirectView.as_view(), name='home'),
]
