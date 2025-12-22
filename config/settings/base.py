# backend/config/settings/base.py
import os
from pathlib import Path

import dj_database_url
# from dotenv import load_dotenv
from corsheaders.defaults import default_headers, default_methods


# Load environment variables from .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# ENV_PATH = BASE_DIR / ".env"
# if ENV_PATH.exists():
#     load_dotenv(ENV_PATH)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-secret-key-change-in-prod")
DEBUG = env.bool("DJANGO_DEBUG", default=False)




import environ
env = environ.Env()
environ.Env.read_env()

# Email config via django-environ (use default= for default values)
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if env.bool("DJANGO_DEBUG", False)
    else "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# Friendly from-name support:
MAIL_FROM_NAME = env("MAIL_FROM_NAME", default="Emma Foundation")
# Prefer explicit DEFAULT_FROM_EMAIL if provided; otherwise construct one
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=f'{MAIL_FROM_NAME} <{EMAIL_HOST_USER or "no-reply@example.com"}>',
)



ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    # Providers
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.twitter",
    "allauth.socialaccount.providers.instagram",
    # Third-party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Local apps
    "accounts",
    "navigation",
    "content",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "pq_test",
    "shopping_mall",
    "channels",
    "msp",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must be high
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if env.bool("USE_REDIS", default=False):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(env("REDIS_HOST", "127.0.0.1"), 6379)],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


# Database: PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "emma"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = f"https://{env('AWS_S3_CUSTOM_DOMAIN')}/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework & JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])


CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
]

CORS_ALLOW_METHODS = list(default_methods)


# Cookies remain Lax/HTTP in dev; host is the same (127.0.0.1) across ports
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", default="None")
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="None")
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)


CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# Custom user model
AUTH_USER_MODEL = "accounts.User"

# -------------------------
# django-allauth / dj-rest-auth
# -------------------------
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

REST_USE_JWT = True

# Optional: store JWT in cookies (good for classic web flows)
JWT_AUTH_COOKIE = "emma-jwt"
JWT_AUTH_REFRESH_COOKIE = "emma-jwt-refresh"
TOKEN_MODEL = None

# -------------------------
# allauth (new settings API)
# -------------------------
# Email-only login
ACCOUNT_LOGIN_METHODS = {"email"}
# Signup fields (new allauth API): declare fields and required flags
ACCOUNT_SIGNUP_FIELDS = {
    "username": {"required": True},
    "email": {"required": True},
}
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_PROVIDERS = {"google": {"SCOPE": ["profile", "email"]}}
LOGIN_REDIRECT_URL = env("LOGIN_REDIRECT_URL", default="/")


# Social login behavior
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"

# Don't pause for email verification (for dev)
ACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"



# Celery (optional)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

# If not configured, Celery tasks run synchronously (safe fallback)
CELERY_TASK_ALWAYS_EAGER = not bool(CELERY_BROKER_URL)
CELERY_TASK_STORE_EAGER_RESULT = False

if CELERY_TASK_ALWAYS_EAGER:
    print("⚠️ Celery is running in synchronous (non-Redis) mode")


# MAIL_FROM_NAME support (compose DEFAULT_FROM_EMAIL)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Emma Foundation")
# If DEFAULT_FROM_EMAIL env provided, prefer it; otherwise build from MAIL_FROM_NAME and EMAIL_HOST_USER
if os.getenv("DEFAULT_FROM_EMAIL"):
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")
else:
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    if EMAIL_HOST_USER:
        DEFAULT_FROM_EMAIL = f"{MAIL_FROM_NAME} <{EMAIL_HOST_USER}>"
    else:
        DEFAULT_FROM_EMAIL = f"{MAIL_FROM_NAME} <no-reply@{os.getenv('EMAIL_DOMAIN','example.com')}>"
