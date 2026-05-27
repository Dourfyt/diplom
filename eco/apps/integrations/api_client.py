"""
HTTP-клиент для платформы «Учёт и переработка промышленных отходов».
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import requests
from django.conf import settings

from apps.integrations.api_token import get_api_access_token
from apps.integrations.exceptions import ApiError


def _request_timeout() -> float | tuple[float, float]:
    connect = getattr(settings, "API_CONNECT_TIMEOUT", 10.0)
    read = getattr(settings, "API_TIMEOUT", 30.0)
    return (connect, read)


def _friendly_request_error(base_url: str, exc: requests.RequestException) -> str:
    if isinstance(exc, requests.Timeout):
        return (
            f"Сервер платформы не ответил вовремя ({base_url}). "
            "Проверьте интернет, VPN или попробуйте позже. "
            "Для работы без сети: USE_REMOTE_API=false в настройках."
        )
    if isinstance(exc, requests.ConnectionError):
        return (
            f"Не удалось подключиться к {base_url}. "
            "Сервер может быть выключен или недоступен из вашей сети."
        )
    return f"Не удалось связаться с API ({base_url}): {exc}"


class ApiClient:
    """Тонкая обёртка над requests для GET/POST/PATCH к API."""

    def __init__(self, base_url: str | None = None, timeout: float | tuple[float, float] | None = None):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else _request_timeout()

    def _url(self, path: str) -> str:
        path = path if path.startswith("/") else f"/{path}"
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
        headers_extra: dict | None = None,
    ) -> Any:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        token = get_api_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if headers_extra:
            headers.update(headers_extra)

        try:
            response = requests.request(
                method.upper(),
                self._url(path),
                json=json_body,
                params=params,
                timeout=self.timeout,
                headers=headers,
            )
        except requests.RequestException as exc:
            raise ApiError(_friendly_request_error(self.base_url, exc)) from exc

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                detail = payload.get("detail", detail)
                if isinstance(detail, list):
                    detail = json.dumps(detail, ensure_ascii=False)
            except (ValueError, AttributeError):
                pass
            raise ApiError(str(detail), status_code=response.status_code)

        if not response.content:
            return None
        return response.json()

    def get(self, path: str, *, params: dict | None = None, headers_extra: dict | None = None) -> Any:
        return self.request("GET", path, params=params, headers_extra=headers_extra)

    def post(self, path: str, json_body: dict | None = None) -> Any:
        return self.request("POST", path, json_body=json_body)

    def patch(self, path: str, json_body: dict | None = None) -> Any:
        return self.request("PATCH", path, json_body=json_body)


def get_client() -> ApiClient:
    return ApiClient()
