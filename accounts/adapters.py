# backend/accounts/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # If a user with this email already exists, attach the social account
        if sociallogin.is_existing:
            return
        email = sociallogin.user.email
        if not email:
            return
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return
        sociallogin.connect(request, existing_user)
