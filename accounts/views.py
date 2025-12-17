# backend/accounts/views.py
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
from django.contrib.auth.hashers import make_password

from .models import (
    AccessLevel,
    ChapterMembership,
    LocalChapter,
    MemberTier,
    UserProfile,
    VerificationCode,
)
from .utils import send_verification_email, send_password_reset_email

from .permissions import HasMinAccessLevel
from .serializers import (
    AccessLevelSerializer,
    RegisterSerializer,
    UserSerializer,
    ProfileSerializer,
    LocalChapterSerializer,
    ChapterMembershipSerializer,
    EmailTokenObtainPairSerializer,
)

User = get_user_model()

class EmailLoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class RegisterView(APIView):
    """
    Step 1 of signup: create signup verification code and store signup data in session.
    Request body: { "email": "...", "username": "...", "password": "...", "access_level": "visitor" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email", "") or "").strip().lower()
        username = (request.data.get("username", "") or "").strip()
        password = request.data.get("password", "")
        access_level = request.data.get("access_level", AccessLevel.VISITOR)

        if not email or not password or not username:
            return Response({"detail": "email, username and password are required."}, status=400)

        if User.objects.filter(email__iexact=email).exists():
            return Response({"detail": "Email already registered. Try password reset or login."}, status=400)

        # create signup verification code with username & password
        vc = VerificationCode.create_for_signup(
            email=email,
            username=username,
            password=password,
            ttl_minutes=15
        )

        ok = send_verification_email(email, vc.code)
        if not ok:
            vc.delete()
            return Response({"detail": "Failed to send verification email."}, status=500)

        # Save signup data in session
        request.session[f"signup_{email}"] = {
            "username": username,
            "password": password,
            "access_level": access_level,
            "created_at": timezone.now().isoformat(),
        }
        request.session.modified = True

        return Response({"detail": "Verification code sent to email."}, status=201)



class ConfirmRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        if not email or not code:
            return Response({"detail": "Email and code are required."}, status=400)

        try:
            vc = VerificationCode.objects.get(email=email, code=code, purpose=VerificationCode.PURPOSE_SIGNUP, is_used=False)
        except VerificationCode.DoesNotExist:
            return Response({"detail": "Invalid email or code."}, status=400)

        if vc.expires_at < timezone.now():
            vc.is_used = True
            vc.save(update_fields=["is_used"])
            return Response({"detail": "Code has expired."}, status=400)

        if User.objects.filter(email__iexact=email).exists():
            vc.is_used = True
            vc.save(update_fields=["is_used"])
            return Response({"detail": "Account already exists."}, status=400)

        with transaction.atomic():
            user = User.objects.create(
                email=email,
                username=vc.signup_username,
                password=vc.signup_password_hash,
                access_level=vc.signup_access_level,
                is_email_verified=True,
            )
            UserProfile.objects.get_or_create(user=user, defaults={"access_level": user.access_level})
            if user.access_level == AccessLevel.MEMBER:
                ChapterMembership.objects.get_or_create(user=user, defaults={"member_tier": MemberTier.TIER_1})

            vc.is_used = True
            vc.user = user
            vc.save(update_fields=["is_used", "user"])

        return Response({"detail": "Account created successfully."}, status=201)


class PasswordResetRequestView(APIView):
    """
    POST { "email": "user@example.com" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email", "") or "").strip().lower()
        if not email:
            raise ValidationError({"detail": "Email is required."})

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal whether user exists
            return Response(
                {"detail": "If an account exists, a reset code has been sent."},
                status=status.HTTP_200_OK,
            )

        vc = VerificationCode.create_for_user(
            user,
            purpose=VerificationCode.PURPOSE_RESET,
            ttl_minutes=15,
        )
        send_password_reset_email(user, vc.code)

        return Response(
            {"detail": "If an account exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST { "email": "...", "code": "123456", "new_password": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email", "") or "").strip().lower()
        code = (request.data.get("code", "") or "").strip()
        new_password = request.data.get("new_password", "")

        if not email or not code or not new_password:
            raise ValidationError({"detail": "Email, code and new password are required."})

        if len(new_password) < 8:
            raise ValidationError({"detail": "New password must be at least 8 characters."})

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # don't reveal
            return Response({"detail": "Invalid code or email."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vc = VerificationCode.objects.get(
                user=user,
                purpose=VerificationCode.PURPOSE_RESET,
                code=code,
                is_used=False,
            )
        except VerificationCode.DoesNotExist:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        if vc.expires_at < timezone.now():
            vc.is_used = True
            vc.save(update_fields=["is_used"])
            return Response({"detail": "Code has expired."}, status=status.HTTP_400_BAD_REQUEST)

        # mark code used & set new password
        vc.is_used = True
        vc.save(update_fields=["is_used"])

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)

class PasswordResetVerifyCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        code = (request.data.get("code") or "").strip()

        if not email or not code:
            return Response({"detail": "Email and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid code or email."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vc = VerificationCode.objects.get(
                user=user,
                purpose=VerificationCode.PURPOSE_RESET,
                code=code,
                is_used=False,
            )
        except VerificationCode.DoesNotExist:
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)

        if vc.expires_at < timezone.now():
            vc.is_used = True
            vc.save(update_fields=["is_used"])
            return Response({"detail": "Code has expired."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Code is valid."}, status=status.HTTP_200_OK)

class ResendSignupCodeView(APIView):
    """
    POST { "email": "someone@example.com" }
    Resend OTP for signup (email that does NOT yet have a user),
    using the signup data stored in the last unused VerificationCode.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Email is required."}, status=400)

        # Do not allow resending for existing accounts
        if User.objects.filter(email__iexact=email).exists():
            return Response({"detail": "Email already registered."}, status=400)

        # Try to find the most recent unused signup code
        vc = VerificationCode.objects.filter(
            email=email,
            purpose=VerificationCode.PURPOSE_SIGNUP,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()

        if vc:
            # Resend the existing code
            code_to_send = vc.code
        else:
            return Response({"detail": "No pending signup found. Please register again."}, status=400)

        ok = send_verification_email(email, code_to_send)
        if not ok:
            return Response({"detail": "Failed to send verification email."}, status=500)

        return Response({"detail": "Verification code resent."}, status=200)

class ResendResetCodeView(APIView):
    """
    POST { "email": "user@example.com" }
    Resend password reset OTP for an existing user.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email", "") or "").strip().lower()
        if not email:
            return Response({"detail": "Email is required."}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # do not reveal
            return Response({"detail": "If an account exists, a reset code has been sent."}, status=200)

        vc = VerificationCode.create_for_user(user=user, purpose=VerificationCode.PURPOSE_RESET, ttl_minutes=15)
        ok = send_password_reset_email(user, vc.code)
        if not ok:
            vc.delete()
            return Response({"detail": "Failed to send reset email."}, status=500)

        return Response({"detail": "If an account exists, a reset code has been sent."}, status=200)

class VerifyResetCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")
        try:
            user = User.objects.get(email__iexact=email)
            vc = VerificationCode.objects.get(user=user, code=code, purpose=VerificationCode.PURPOSE_RESET, is_used=False)
            if vc.expires_at < timezone.now():
                return Response({"detail": "Code expired"}, status=400)
        except (User.DoesNotExist, VerificationCode.DoesNotExist):
            return Response({"detail": "Invalid code"}, status=400)
        return Response({"detail": "Code valid"})

# The remaining views unchanged from your file:
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class AccessLevelListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        choices = [{"code": code, "label": label} for code, label in AccessLevel.choices]
        serializer = AccessLevelSerializer(choices, many=True)
        return Response(serializer.data)


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_object(self):
        profile_obj, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile_obj

    def perform_update(self, serializer):
        serializer.save(user=self.request.user, access_level=self.request.user.access_level)


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        with transaction.atomic():
            user = request.user
            user.delete()
        return Response(status=204)


class LocalChapterListCreateView(generics.ListCreateAPIView):
    queryset = LocalChapter.objects.all().order_by("name")
    serializer_class = LocalChapterSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [HasMinAccessLevel.with_level("admin")()]


class LocalChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LocalChapter.objects.all()
    serializer_class = LocalChapterSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [HasMinAccessLevel.with_level("admin")()]


class MembershipView(generics.RetrieveUpdateAPIView):
    serializer_class = ChapterMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        membership, _ = ChapterMembership.objects.get_or_create(user=self.request.user, defaults={"member_tier": MemberTier.TIER_1})
        return membership

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
