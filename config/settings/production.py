from .base import *

DEBUG = False

# In production you must set ALLOWED_HOSTS via env
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

CSRF_TRUSTED_ORIGINS = [
    "https://www.PlutusInvestment.com",
    "https://www.PlutusInvestment.com",
]

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
