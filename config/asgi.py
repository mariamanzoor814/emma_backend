# backend/config/asgi.py
"""
ASGI config for EMMA project using Django Channels.

Routes:
- HTTP      -> normal Django ASGI app
- websocket -> pq_test.websocket_urlpatterns (with JWT auth)
"""

import os

# 1) Configure settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# 2) Setup Django BEFORE importing anything that touches models
import django
django.setup()

# 3) Now it's safe to import Django/Channels/pq_test stuff
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from pq_test.jwt_middleware import JWTAuthMiddlewareStack
import pq_test.routing  # websocket routes

# 4) HTTP ASGI app
django_asgi_app = get_asgi_application()

# 5) Combined ASGI application
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(pq_test.routing.websocket_urlpatterns)
        ),
    }
)
