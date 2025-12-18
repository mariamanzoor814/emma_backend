# backend/config/urls.py
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path("admin/", admin.site.urls),

    # Your custom auth endpoints
    path("accounts/", include("accounts.urls", namespace="accounts-public")),
    # dj-rest-auth (social + session endpoints)
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/registration/", include("dj_rest_auth.registration.urls")),

    path("api/navigation/", include("navigation.urls", namespace="navigation")),
    path("api/content/", include("content.urls", namespace="content")),
    path("accounts/", include("allauth.urls")),
    path("api/pq/", include("pq_test.urls")),
    path("api/mall/", include("shopping_mall.urls", namespace="shopping_mall")),
    path('api/msp/', include('msp.urls'))

    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)