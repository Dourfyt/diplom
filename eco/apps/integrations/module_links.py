"""Ссылки на соседние модули комплекса (UI)."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class SiblingModule:
    id: str
    label: str
    url: str
    current: bool = False


def get_sibling_modules(current_id: str) -> list[SiblingModule]:
    modules = [
        SiblingModule("api", "API платформы", settings.MODULE_API_URL),
        SiblingModule("planning", "Планирование", settings.MODULE_PLANNING_URL),
        SiblingModule("eco", "Отчётность", settings.MODULE_ECO_URL),
    ]
    return [
        SiblingModule(m.id, m.label, m.url, current=(m.id == current_id))
        for m in modules
    ]
