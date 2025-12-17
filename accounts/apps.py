# backend/accounts/apps.py
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "User Management"   # 👈 Add this line

    def ready(self):
        # Import signals so they get registered
        from . import signals  # noqa: F401
