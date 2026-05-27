"""Передаёт JWT из сессии Django в HTTP-запросы к API."""

from apps.integrations.api_token import clear_api_access_token, set_api_access_token


class ApiTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = request.session.get("api_access_token")
        if token:
            set_api_access_token(token)
        try:
            return self.get_response(request)
        finally:
            clear_api_access_token()
