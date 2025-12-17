# backend/pq_test/apps.py
from django.apps import AppConfig


class PqTestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pq_test"
