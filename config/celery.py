# backend/config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

app = Celery("config")

broker = os.getenv("CELERY_BROKER_URL")
backend = os.getenv("CELERY_RESULT_BACKEND")

if broker and backend:
    app.conf.broker_url = broker
    app.conf.result_backend = backend
else:
    # Run tasks locally if no Redis configured
    app.conf.task_always_eager = True
    app.conf.task_store_eager_result = False

app.autodiscover_tasks()
