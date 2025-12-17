# backend/accounts/serializers.py
from django.db import transaction, IntegrityError
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.password_validation import validate_password

from .models import (
    AccessLevel,
    UserProfile,
    ProfileHistory,
    ChapterMembership,
    MemberTier,
    LocalChapter,
)

User = get_user_model()


# 0) SimpleJWT login via email
class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD
    default_error_messages = {
        "no_active_account": "Unable to log in with that email and password.",
    }
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user
        if not user.is_email_verified:
            raise AuthenticationFailed("Please verify your email before logging in.")

        return data



# 1) Access levels are NOT a model – simple serializer
class AccessLevelSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


# 2) User serializer – expose access_level code + label
class UserSerializer(serializers.ModelSerializer):
    # access_level is stored as a CharField on the User model
    access_level = serializers.CharField(read_only=True)
    access_level_label = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "access_level",        # e.g. "owner"
            "access_level_label",  # e.g. "Owner & Super Administrator"
            "avatar_url",
        ]

    def get_access_level_label(self, obj):
        return obj.get_access_level_display()

    def get_avatar_url(self, obj):
        try:
            avatar = getattr(obj.profile, "avatar", None)
            if avatar and hasattr(avatar, "url"):
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(avatar.url)
                return avatar.url
        except Exception:
            return None
        return None


# 3) Registration – use AccessLevel.choices
class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True, allow_blank=False)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    access_level = serializers.ChoiceField(
        choices=AccessLevel.choices,
        required=False,
        default=AccessLevel.VISITOR,
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "access_level")
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Try logging in instead."
            )
        return email

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError("Username is required.")
        if len(username) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters.")
        if not User.username_validator.regex.match(username):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, or hyphens."
            )
        return username

    def validate_password(self, value):
        # Use Django password validators and ensure minimum length
        try:
            validate_password(value)
        except Exception as e:
            # validate_password may raise ValidationError or list of messages
            raise serializers.ValidationError(list(e.messages) if hasattr(e, "messages") else str(e))
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        access_level = validated_data.pop("access_level", AccessLevel.VISITOR)
        password = validated_data.pop("password")
        email = validated_data.pop("email").strip().lower()
        username = validated_data.pop("username").strip() or email

        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                username=username,
                access_level=access_level,
                is_email_verified=False,
            )
        except IntegrityError:
            raise serializers.ValidationError(
                {"email": "An account with this email already exists. Try logging in instead."}
            )

        # Ensure profile exists and access_level is consistent
        UserProfile.objects.get_or_create(user=user, defaults={"access_level": access_level})
        if access_level == AccessLevel.MEMBER:
            ChapterMembership.objects.get_or_create(user=user, defaults={"member_tier": MemberTier.TIER_1})

        return user


# 4) Profile serializer – also use AccessLevel.choices
class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    access_level = serializers.ChoiceField(choices=AccessLevel.choices, required=False)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "access_level",
            "background",
            "education",
            "interests",
            "iq_score",
            "eq_score",
            "gq_score",
            "phone",
            "date_of_birth",
            "gender",
            "country",
            "city",
            "address",
            "location",
            "bio",
            "about",
            "avatar",
            "avatar_url",
            "profession",
            "organization",
            "extra",
            "net_worth",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "user", "created_at", "updated_at", "avatar_url")

    def update(self, instance, validated_data):
        # keep user binding immutable
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

    def get_avatar_url(self, obj):
        avatar = getattr(obj, "avatar", None)
        if avatar and hasattr(avatar, "url"):
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(avatar.url)
            return avatar.url
        return None


class LocalChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalChapter
        fields = [
            "id",
            "name",
            "code",
            "country",
            "city",
            "address",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class ChapterMembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    chapter = LocalChapterSerializer(read_only=True)
    chapter_id = serializers.PrimaryKeyRelatedField(
        queryset=LocalChapter.objects.all(),
        source="chapter",
        write_only=True,
        required=False,
        allow_null=True,
    )
    member_tier = serializers.ChoiceField(choices=MemberTier.choices, required=False)

    class Meta:
        model = ChapterMembership
        fields = [
            "id",
            "user",
            "chapter",
            "chapter_id",
            "member_tier",
            "rating_score",
            "rating_notes",
            "joined_at",
            "updated_at",
        ]
        read_only_fields = ("id", "joined_at", "updated_at")

    def update(self, instance, validated_data):
        validated_data.pop("user", None)
        return super().update(instance, validated_data)

def verify_email(user, code):
    try:
        vc = VerificationCode.objects.get(
            user=user, code=code, purpose=VerificationCode.PURPOSE_SIGNUP, is_used=False
        )
    except VerificationCode.DoesNotExist:
        raise serializers.ValidationError("Invalid code.")

    if vc.expires_at < timezone.now():
        raise serializers.ValidationError("Code expired.")

    vc.is_used = True
    vc.save()
    user.is_email_verified = True
    user.save(update_fields=["is_email_verified"])
    return True
