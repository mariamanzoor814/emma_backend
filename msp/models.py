# File: backend/msp/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

class RawFirm(models.Model):
    """Immutable staging row (store full source row in raw_payload)."""
    source = models.CharField(max_length=64)
    source_id = models.CharField(max_length=128, blank=True)

    company_name = models.CharField(max_length=512)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)

    country = models.CharField(max_length=64, blank=True)
    state = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)

    raw_payload = models.JSONField()

    imported_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['source', 'source_id']),
            models.Index(fields=['company_name']),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.source})"


class CandidateFirm(models.Model):
    raw_firm = models.OneToOneField(
        RawFirm,
        on_delete=models.CASCADE,
        related_name='candidate',
    )

    score = models.FloatField(default=0.0)
    matched_rules = models.JSONField(default=list, blank=True)

    is_us = models.BooleanField(default=False)
    suspected_msp = models.BooleanField(default=False)
    suspected_pe = models.BooleanField(default=False)

    STATUS_PENDING = 'pending'
    STATUS_REJECTED = 'rejected'
    STATUS_VERIFIED = 'verified'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_VERIFIED, 'Verified'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # Assignment / locking fields
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_candidates",
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locked_candidates",
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    last_called_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'score']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['locked_at']),
        ]

    def __str__(self):
        return f"Candidate({self.raw_firm.company_name[:60]})"

    def claim(self, user):
        """
        Attempt to claim this candidate for `user`. Returns True if claimed.
        """
        if self.locked_by and (timezone.now() - (self.locked_at or timezone.now())).total_seconds() < 600:
            # locked in last 10 minutes
            return False
        self.locked_by = user
        self.locked_at = timezone.now()
        self.assigned_to = user
        self.save(update_fields=['locked_by', 'locked_at', 'assigned_to', 'updated_at'])
        return True


class CallVerification(models.Model):
    candidate = models.ForeignKey(
        CandidateFirm,
        on_delete=models.CASCADE,
        related_name='calls',
    )

    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    CONTACT_CALL = 'call'
    CONTACT_EMAIL = 'email'

    CONTACT_CHOICES = [
        (CONTACT_CALL, 'Call'),
        (CONTACT_EMAIL, 'Email'),
    ]

    RESULT_NO_ANSWER = 'no_answer'
    RESULT_NOT_MSP = 'not_msp'
    RESULT_NOT_PE = 'not_pe'
    RESULT_CONFIRMED = 'confirmed'
    RESULT_INVALID = 'invalid_contact'

    RESULT_CHOICES = [
        (RESULT_NO_ANSWER, 'No Answer'),
        (RESULT_NOT_MSP, 'Not MSP'),
        (RESULT_NOT_PE, 'Not PE'),
        (RESULT_CONFIRMED, 'Confirmed'),
        (RESULT_INVALID, 'Invalid Contact'),
    ]

    contact_method = models.CharField(
        max_length=20,
        choices=CONTACT_CHOICES,
        default=CONTACT_CALL,
    )

    result = models.CharField(
        max_length=32,
        choices=RESULT_CHOICES,
        blank=True,
        null=True,
    )

    notes = models.TextField(blank=True)
    called_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['candidate', 'called_at']),
        ]

    def __str__(self):
        return f"Call({self.candidate.raw_firm.company_name[:30]} by {self.caller})"


class VerifiedMSPFirm(models.Model):
    candidate = models.OneToOneField(
        CandidateFirm,
        on_delete=models.CASCADE,
        related_name='verified',
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )

    verified_at = models.DateTimeField(auto_now_add=True)
    confidence = models.IntegerField(default=3)  # 1–5
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['verified_at']),
        ]

    def __str__(self):
        return f"Verified({self.candidate.raw_firm.company_name[:60]})"


# --- Signals to auto-update candidate status and create VerifiedMSPFirm ---
@receiver(post_save, sender=CallVerification)
def handle_call_verification(sender, instance: CallVerification, created, **kwargs):
    if not created:
        return

    candidate = instance.candidate
    candidate.last_called_at = instance.called_at

    # Keep status as pending if not verified yet
    if candidate.status != CandidateFirm.STATUS_VERIFIED:
        candidate.status = CandidateFirm.STATUS_PENDING
    candidate.save(update_fields=['last_called_at', 'updated_at', 'status'])

    # Auto-create VerifiedMSPFirm if call confirmed
    if instance.result == CallVerification.RESULT_CONFIRMED:
        vc, created = VerifiedMSPFirm.objects.get_or_create(
            candidate=candidate,
            defaults={'verified_by': instance.caller, 'confidence': 3}
        )
        candidate.status = CandidateFirm.STATUS_VERIFIED
        candidate.save(update_fields=['status', 'updated_at'])
