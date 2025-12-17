# backend/pq_test/routing.py
from django.urls import re_path

from .consumers import QuizSessionConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/pq/sessions/(?P<session_code>[\w-]+)/$",
        QuizSessionConsumer.as_asgi(),
    ),
]
