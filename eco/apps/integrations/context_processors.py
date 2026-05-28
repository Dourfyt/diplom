from django.conf import settings

from apps.integrations.module_links import get_sibling_modules
from apps.integrations.nav_active import resolve_nav_active
from apps.integrations.roles import (
    can_access_dashboard,
    get_home_redirect_url_for_user,
    get_user_role_label,
    is_admin,
    is_ecologist,
    is_manager,
)


def api_integration(request):
    user = request.user
    ctx = {
        "use_remote_api": settings.USE_REMOTE_API,
        "use_api_auth": getattr(settings, "USE_API_AUTH", False),
        "api_base_url": settings.API_BASE_URL,
        "sibling_modules": get_sibling_modules("eco"),
        "nav_active": resolve_nav_active(request),
    }
    if user.is_authenticated:
        su = user.is_superuser
        ctx.update(
            {
                "user_home_url": get_home_redirect_url_for_user(user),
                "user_role_label": get_user_role_label(user),
                "can_access_platform_docs": True,
                "can_access_admin_panel": False,
                "can_access_organizations": su or is_admin(user),
                "can_access_batches": su or is_admin(user),
                "can_access_users": su,
                "can_access_modules": su,
                "can_access_waste": su or is_admin(user),
                "can_access_operations": su or is_ecologist(user),
                "can_access_monitoring": su or is_ecologist(user),
                "can_access_dashboard": su or can_access_dashboard(user),
            }
        )
    else:
        ctx.update(
            {
                "user_home_url": "/accounts/login/",
                "user_role_label": "",
                "can_access_admin_panel": False,
                "can_access_organizations": False,
                "can_access_batches": False,
                "can_access_users": False,
                "can_access_modules": False,
                "can_access_waste": False,
                "can_access_operations": False,
                "can_access_monitoring": False,
                "can_access_dashboard": False,
            }
        )
    return ctx
