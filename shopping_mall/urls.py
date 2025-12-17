from django.urls import path
from .views import StorefrontAPIView

app_name = "shopping_mall"

urlpatterns = [
    path("storefront/", StorefrontAPIView.as_view(), name="storefront"),
]
