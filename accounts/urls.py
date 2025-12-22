# backend/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AccessLevelListView,
    MeView,
    RegisterView,
    ProfileDetailView,
    LocalChapterListCreateView,
    LocalChapterDetailView,
    MembershipView,
    DeleteAccountView,
    EmailLoginView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    ResendSignupCodeView,
    ResendResetCodeView,
    ConfirmRegistrationView,
    PasswordResetVerifyCodeView
)
from .social_views import social_start, social_jwt

app_name = "accounts"

urlpatterns = [
    # Auth / JWT
    path("login/", EmailLoginView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Social Auth
    path("social/login/", social_jwt, name="social_jwt"),
    path("social-start/<str:provider>/", social_start, name="social_login"),

    # Registration flow
    path("register/", RegisterView.as_view(), name="register"),  # sends signup OTP
    path("confirm-registration/", ConfirmRegistrationView.as_view(), name="confirm_registration"),  # confirm OTP -> create user
    path("auth/resend-signup/", ResendSignupCodeView.as_view(), name="resend-signup"),
    # Password reset
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("auth/resend-reset/", ResendResetCodeView.as_view(), name="resend-reset"),
    path("password-reset/verify/", PasswordResetVerifyCodeView.as_view(), name="password_reset_verify"),

    # Current user
    path("me/", MeView.as_view(), name="me"),
    path("profile/", ProfileDetailView.as_view(), name="profile"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),

    # Access levels
    path("access-levels/", AccessLevelListView.as_view(), name="access_levels"),

    # Chapters & membership
    path("chapters/", LocalChapterListCreateView.as_view(), name="chapters"),
    path("chapters/<int:pk>/", LocalChapterDetailView.as_view(), name="chapter_detail"),
    path("membership/", MembershipView.as_view(), name="membership"),
]
