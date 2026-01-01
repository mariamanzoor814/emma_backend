# backend/accounts/social_views.py
from django.conf import settings
from django.contrib.auth import login as django_login
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

# allauth provider login URLs:
PROVIDER_LOGIN_URLS = {
    "google": "/accounts/google/login/",
    "twitter": "/accounts/twitter/login/",      # X (Twitter)
    "instagram": "/accounts/instagram/login/",
}

@api_view(["GET"])
@permission_classes([AllowAny])
def social_start(request, provider):
    """
    Redirect user to allauth provider login.
    After successful login, allauth returns to /accounts/social/login/callback/
    We'll override that by giving next=/api/auth/social/callback/?provider=...
    """
    if provider not in PROVIDER_LOGIN_URLS:
        return Response({"detail": "Unknown provider"}, status=400)

    frontend_callback = request.GET.get(
        "callback",
        settings.SOCIALACCOUNT_DEFAULT_REDIRECT_URL # your Next.js callback page
    )

    # allauth uses "next" param for redirect after login
    login_url = PROVIDER_LOGIN_URLS[provider]
    return redirect(f"{login_url}?next={frontend_callback}")

@api_view(["GET"])
@permission_classes([AllowAny])
def social_jwt(request):
    """
    If user is logged in via Django session, mint JWT pair
    so frontend can store it just like normal login.
    """
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return Response({"detail": "Not authenticated"}, status=401)

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    })
