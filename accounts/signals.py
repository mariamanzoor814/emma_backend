# backend/accounts/signals.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, ProfileHistory, AccessLevel


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """
    Create UserProfile safely without crashing if fields change.
    Also prevent duplicate profile creation.
    """
    if not created:
        return

    UserProfile.objects.get_or_create(
        user=instance,
        defaults={
            "access_level": getattr(instance, "access_level", AccessLevel.VISITOR),
            # Add defaults for ANY required fields:
            "background": "",
            "education": "",
            "interests": "",
            "iq_score": None,
            "eq_score": None,
            "gq_score": None,
            "net_worth": None,
        }
    )


@receiver(post_save, sender=UserProfile)
def snapshot_profile_history(sender, instance, created, **kwargs):
    """
    Snapshot profile changes.
    """
    ProfileHistory.objects.create(
        profile=instance,
        access_level=instance.access_level,
        background=instance.background,
        education=instance.education,
        interests=instance.interests,
        iq_score=instance.iq_score,
        eq_score=instance.eq_score,
        gq_score=instance.gq_score,
        net_worth=instance.net_worth,
    )
