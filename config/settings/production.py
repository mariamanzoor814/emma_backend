from .base import *

DEBUG = False

# In production you must set ALLOWED_HOSTS via env
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False


ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

CSRF_TRUSTED_ORIGINS = [
    "http://51.20.194.196/",
]

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
