# backend/accounts/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import secrets
from datetime import timedelta

# 1) Access levels enum
# accounts/models.py

class AccessLevel(models.TextChoices):
    OWNER = "owner", "Owner & Super Administrator"
    DEVELOPER = "developer", "Developer / Programmer"
    ADMIN = "admin", "Administrator"
    CHAPTER_HEAD = "chapter_head", "Head of Local Chapter"
    MEMBER = "member", "End User / Member"
    VISITOR = "visitor", "Visitor"
    PEE_MEMBER = "pee_member", "Private Equity Exchange Member"


ACCESS_LEVEL_ORDER = [
    AccessLevel.VISITOR,
    AccessLevel.MEMBER,
    AccessLevel.CHAPTER_HEAD,
    AccessLevel.ADMIN,
    AccessLevel.DEVELOPER,
    AccessLevel.PEE_MEMBER,
    AccessLevel.OWNER,
]


def has_min_access(user_access: str | None, required: str | None) -> bool:
    """
    If required is None => public.
    Else check if user_access rank >= required rank.
    Anonymous users have access_level = None.
    """
    if not required:
        return True  # public

    if not user_access:
        return False  # anonymous

    try:
        user_idx = ACCESS_LEVEL_ORDER.index(user_access)
        req_idx = ACCESS_LEVEL_ORDER.index(required)
    except ValueError:
        return False

    return user_idx >= req_idx


class EmailUserManager(UserManager):
    """
    Use email as the login identifier while keeping an optional username.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set")

        email = self.normalize_email(email)
        username = extra_fields.pop("username", "") or email

        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("access_level", AccessLevel.OWNER)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username_validator = RegexValidator(
        regex=r"^[A-Za-z0-9_-]+$",
        message="Username can only contain letters, numbers, underscores, or hyphens.",
    )

    username = models.CharField(
        _("username"),
        max_length=150,
        blank=False,
        validators=[username_validator],
    )
    email = models.EmailField(_("email address"), unique=True)
    access_level = models.CharField(
        max_length=32,
        choices=AccessLevel.choices,
        default=AccessLevel.VISITOR,
    )

    # NEW: email verification flag
    is_email_verified = models.BooleanField(default=False)

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = EmailUserManager()

    def __str__(self) -> str:
        return self.email or self.username or f"User {self.pk}"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    access_level = models.CharField(
        max_length=32,
        choices=AccessLevel.choices,
        default=AccessLevel.VISITOR,
    )

    background = models.TextField(blank=True)
    education = models.TextField(blank=True)
    interests = models.TextField(blank=True)

    iq_score = models.FloatField(null=True, blank=True)
    eq_score = models.FloatField(null=True, blank=True)
    gq_score = models.FloatField(null=True, blank=True)

    # --- Full account-holder details (EMMA doc / Excel driven) ---
    phone = models.CharField(max_length=32, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=32, blank=True)

    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    about = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    profession = models.CharField(max_length=120, blank=True)
    organization = models.CharField(max_length=160, blank=True)

    # keep a flexible JSON bucket for future Excel columns
    extra = models.JSONField(default=dict, blank=True)

    net_worth = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        identifier = self.user.username or self.user.email or self.user_id
        return f"Profile({identifier}, {self.access_level})"


class ProfileHistory(models.Model):
    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="history",
    )
    access_level = models.CharField(max_length=32)
    background = models.TextField(blank=True)
    education = models.TextField(blank=True)
    interests = models.TextField(blank=True)
    iq_score = models.FloatField(null=True, blank=True)
    eq_score = models.FloatField(null=True, blank=True)
    gq_score = models.FloatField(null=True, blank=True)
    net_worth = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    snapshot_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return f"ProfileHistory({self.profile_id} at {self.snapshot_at})"
    
class LocalChapter(models.Model):
    """
    Represents a local EMMA chapter (city/country level).
    Each chapter has a head (User) with access_level=CHAPTER_HEAD.
    """
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=32, unique=True)  # e.g., "KHI-001"
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)

    head = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chapter_head_of",
        limit_choices_to={"access_level": AccessLevel.CHAPTER_HEAD},
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class MemberTier(models.TextChoices):
    """
    7-tiered rating system for members.
    You can rename labels to whatever EMMA doc says later.
    """
    TIER_1 = "tier_1", "Tier 1"
    TIER_2 = "tier_2", "Tier 2"
    TIER_3 = "tier_3", "Tier 3"
    TIER_4 = "tier_4", "Tier 4"
    TIER_5 = "tier_5", "Tier 5"
    TIER_6 = "tier_6", "Tier 6"
    TIER_7 = "tier_7", "Tier 7"


class ChapterMembership(models.Model):
    """
    Links a user to a local chapter + stores their 7-tier rating.
    Only meaningful for access_level=MEMBER, but leaving flexible.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chapter_membership",
    )
    chapter = models.ForeignKey(
        LocalChapter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
    )

    member_tier = models.CharField(
        max_length=20,
        choices=MemberTier.choices,
        default=MemberTier.TIER_1,
    )

    # optional scoring fields for your rating algorithm
    rating_score = models.FloatField(default=0.0)  # computed by your system
    rating_notes = models.TextField(blank=True)

    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        identifier = self.user.username or self.user.email or self.user_id
        return f"{identifier} -> {self.chapter} ({self.member_tier})"

class VerificationCode(models.Model):
    PURPOSE_SIGNUP = "signup"
    PURPOSE_RESET = "reset_password"
    PURPOSE_CHOICES = [
        (PURPOSE_SIGNUP, "Signup verification"),
        (PURPOSE_RESET, "Password reset"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_codes",
        null=True,
        blank=True,
    )
    email = models.EmailField(null=True, blank=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    # NEW: store signup data
    signup_username = models.CharField(max_length=150, null=True, blank=True)
    signup_password_hash = models.CharField(max_length=128, null=True, blank=True)
    signup_access_level = models.CharField(max_length=32, null=True, blank=True)

    @staticmethod
    def generate_code() -> str:
        return f"{secrets.randbelow(1000000):06d}"

    @classmethod
    def create_for_signup(cls, email: str, username: str, password: str, access_level: str = "visitor", ttl_minutes: int = 1):
        cls.objects.filter(
            email=email,
            purpose=cls.PURPOSE_SIGNUP,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).update(is_used=True)

        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)
        from django.contrib.auth.hashers import make_password
        return cls.objects.create(
            email=email,
            code=code,
            purpose=cls.PURPOSE_SIGNUP,
            expires_at=expires_at,
            signup_username=username,
            signup_password_hash=make_password(password),
            signup_access_level=access_level
        )
    @classmethod
    def create_for_user(cls, user, purpose: str = PURPOSE_RESET, ttl_minutes: int = 15) -> "VerificationCode":
        """
        Create a new verification code for an existing user (e.g., password reset).

        Marks any previous unused codes of the same purpose as used.
        """
        # Expire any existing unused codes for this user/purpose
        cls.objects.filter(
            user=user,
            purpose=purpose,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).update(is_used=True)

        # Generate new code
        code = f"{secrets.randbelow(1000000):06d}"
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

        return cls.objects.create(
            user=user,
            email=user.email,
            code=code,
            purpose=purpose,
            expires_at=expires_at,
        )
