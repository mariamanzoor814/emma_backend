# backend/pq_test/jwt_middleware.py
import urllib.parse

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


@database_sync_to_async
def _get_user_for_token(token: str):
    try:
        auth = JWTAuthentication()
        validated = auth.get_validated_token(token)
        return auth.get_user(validated)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WS middleware that authenticates with JWT (header or ?token=).
    """

    async def __call__(self, scope, receive, send):
        token = None

        # Authorization: Bearer <token>
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        if auth_header:
            try:
                parts = auth_header.decode().split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
            except Exception:
                pass

        # Fallback query param: ?token=<jwt>
        if not token:
            query_string = scope.get("query_string", b"").decode()
            if query_string:
                qs = urllib.parse.parse_qs(query_string)
                token = qs.get("token", [None])[0]

        user = await _get_user_for_token(token) if token else AnonymousUser()
        scope = dict(scope)
        scope["user"] = user

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))
