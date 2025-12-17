# backend/content/views.py
from django.shortcuts import get_object_or_404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied

from .models import Page
from .serializers import PageDetailSerializer
from accounts.models import has_min_access  # 👈 import helper


class PageDetailView(APIView):
    """
    GET /api/content/pages/<slug>/?lang=en
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, slug: str):
        lang = request.query_params.get("lang", "en")

        page = get_object_or_404(Page, slug=slug, is_active=True)

        # Access-level protection using single CharField
        required = page.access_level  # may be None (public)
        user = request.user if request.user.is_authenticated else None
        user_access = getattr(user, "access_level", None) if user else None

        if not has_min_access(user_access, required):
            raise PermissionDenied("Not allowed to view this page.")

        serializer = PageDetailSerializer(
            page,
            context={
                "language": lang,
                "request": request,  # 🔥 needed for absolute image URLs
            },
        )

        return Response(serializer.data)
