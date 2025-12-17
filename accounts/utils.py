# backend/accounts/utils.py
import logging
from django.conf import settings
from django.core.mail import send_mail, BadHeaderError

logger = logging.getLogger(__name__)

def send_verification_email(user_or_email, code: str):
    if isinstance(user_or_email, str):
        email = user_or_email
        username = ""
    else:
        email = user_or_email.email
        username = user_or_email.username or user_or_email.email

    subject = "Verify your EMMA account"
    message = (
        f"Hi {username},\n\n"
        f"Your EMMA verification code is: {code}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
        logger.info("Sent verification email to %s", email)
        return True
    except Exception as e:
        logger.exception("Failed to send verification email to %s: %s", email, e)
        return False


def send_password_reset_email(user, code: str):
    subject = "EMMA password reset code"
    message = (
        f"Hi {user.username or user.email},\n\n"
        f"Your EMMA password reset code is: {code}\n\n"
        f"This code will expire in 15 minutes.\n\n"
        "If you did not request a password reset, you can ignore this email."
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
    try:
        send_mail(subject, message, from_email, [user.email], fail_silently=False)
        logger.info("Sent password reset email to %s", user.email)
    except Exception as e:
        logger.exception("Failed to send password reset email to %s: %s", user.email, e)
        return False
    return True
