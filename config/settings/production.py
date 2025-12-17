from .base import *

DEBUG = False

# In production you must set ALLOWED_HOSTS via env
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
