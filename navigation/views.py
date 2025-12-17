# backend/navigation/views.py
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MenuItem
from .serializers import MenuItemSerializer
from accounts.models import has_min_access  # 👈 import helper


class MenuListView(APIView):
    """
    Returns menu items for a given position (top/main/footer),
    filtered by the current user's access level.

    Frontend usage:
      GET /api/navigation/menus?position=top
      GET /api/navigation/menus?position=main
    """

    permission_classes = [AllowAny]

    def get(self, request):
        position = request.query_params.get("position")

        # top-level items only
        qs = MenuItem.objects.filter(is_active=True, parent__isnull=True)

        if position:
            qs = qs.filter(position=position)

        # current user + access level string (or None)
        user = request.user if request.user.is_authenticated else None
        user_access = getattr(user, "access_level", None) if user else None

        # filter parents by access_level (children filtered in serializer)
        visible_items = [
            item for item in qs if has_min_access(user_access, item.access_level)
        ]

        serializer = MenuItemSerializer(
            visible_items,
            many=True,
            context={"request": request},  # 👈 ensures child serializer gets request
        )
        return Response(serializer.data)
