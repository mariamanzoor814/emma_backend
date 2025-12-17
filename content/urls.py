# backend/content/urls.py
from django.urls import path, include

from .views import PageDetailView

app_name = "content"

urlpatterns = [
    path("pages/<slug:slug>/", PageDetailView.as_view(), name="page_detail"),
]
