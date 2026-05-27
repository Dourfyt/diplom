"""Токен API текущего запроса (JWT после входа на сервере)."""

from __future__ import annotations

import contextvars

_api_access_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "api_access_token",
    default=None,
)


def set_api_access_token(token: str | None) -> None:
    _api_access_token.set(token)


def get_api_access_token() -> str | None:
    return _api_access_token.get()


def clear_api_access_token() -> None:
    _api_access_token.set(None)
