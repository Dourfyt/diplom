"""Определение активного пункта главного меню по URL."""

from __future__ import annotations


def resolve_nav_active(request) -> str:
    path = getattr(request, "path", "") or ""
    match = getattr(request, "resolver_match", None)
    namespace = getattr(match, "namespace", None) or ""
    url_name = getattr(match, "url_name", None) or ""

    if path.startswith("/dashboard/reporting"):
        return "reporting"
    if path.startswith("/dashboard"):
        return "dashboard"
    if path.startswith("/operations"):
        return "operations"
    if path.startswith("/monitoring"):
        return "monitoring"
    if path.startswith("/waste"):
        return "waste"
    if path.startswith("/manage/data-control"):
        return "data_control"
    if path.startswith("/manage/organizations"):
        return "organizations"
    if path.startswith("/manage/batches"):
        return "batches"
    if path.startswith("/manage/modules"):
        return "modules"
    if path.startswith("/manage/users"):
        return "users"

    if namespace == "dashboard":
        return "reporting" if url_name == "reporting" else "dashboard"
    if namespace == "operations":
        return "operations"
    if namespace == "monitoring":
        return "monitoring"
    if namespace == "waste":
        return "waste"
    if namespace == "administration":
        mapping = {
            "organizations": "organizations",
            "organization_detail": "organizations",
            "data_control": "data_control",
            "batches": "batches",
            "modules": "modules",
            "user_register": "users",
        }
        return mapping.get(url_name, "")

    return ""
