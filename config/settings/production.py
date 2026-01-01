from .base import *

DEBUG = False

# In production you must set ALLOWED_HOSTS via env
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")

ALLOWED_HOSTS = ["plutusinvestment.com", "www.plutusinvestment.com", "api.plutusinvestment.com"]

CSRF_TRUSTED_ORIGINS = ["https://plutusinvestment.com", "https://www.plutusinvestment.com", "https://api.plutusinvestment.com",]

# CSRF_TRUSTED_ORIGINS = [
#     "https://plutusinvestment.com",
#     "https://www.plutusinvestment.com",
# ]

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SOCIALACCOUNT_DEFAULT_REDIRECT_URL = "https://api.plutusinvestment.com/accounts/google/login/callback/"
LOGIN_REDIRECT_URL = "https://plutusinvestment.com/auth/callback"

