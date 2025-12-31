# backend/config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static


from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from accounts.social_views import social_start, social_jwt

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

urlpatterns = [
    path("", lambda r: HttpResponse("API is running")),
    path("admin/", admin.site.urls),

    # Your custom auth endpoints
    path("accounts/", include("accounts.urls", namespace="accounts-public")),
    # dj-rest-auth (social + session endpoints)
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),
    

    path("api/navigation/", include("navigation.urls", namespace="navigation")),
    path("api/content/", include("content.urls", namespace="content")),
    
    # Explicitly define social start to diagnose routing issue
    path("accounts/social-start/<str:provider>/", social_start, name="social_start_root"),
    path("accounts/", include("allauth.urls")),
    path("api/pq/", include("pq_test.urls")),
    path("api/mall/", include("shopping_mall.urls", namespace="shopping_mall")),
    path('api/msp/', include('msp.urls')),
    # path("api/auth/google/", GoogleLogin.as_view(), name="google_login"),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
