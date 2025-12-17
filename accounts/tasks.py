# backend/accounts/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, subject, message, from_email, recipient_list):
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        logger.info("Celery: Sent verification email to %s", recipient_list)
        return True
    except Exception as exc:
        logger.exception("Celery: Failed to send verification email to %s: %s", recipient_list, exc)
        # retry with exponential backoff
        raise self.retry(exc=exc)
