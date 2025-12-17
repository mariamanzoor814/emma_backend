# backend/navigation/serializers.py
from rest_framework import serializers

from .models import MenuItem
from accounts.models import has_min_access  # 👈 import helper


class MenuItemSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            "id",
            "title_key",
            "slug",
            "path",
            "position",
            "order",
            "open_in_new_tab",
            "access_level",   # 👈 expose if you want (optional but useful)
            "children",
        ]

    def get_children(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        user_access = (
            getattr(user, "access_level", None)
            if user is not None and user.is_authenticated
            else None
        )

        children_qs = obj.children.filter(is_active=True).order_by("order")

        # filter by access_level using helper
        visible_children = [
            child
            for child in children_qs
            if has_min_access(user_access, child.access_level)
        ]

        return MenuItemSerializer(
            visible_children,
            many=True,
            context=self.context,  # 👈 keep request in nested serializer too
        ).data
