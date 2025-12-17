# backend/accounts/permissions.py
from rest_framework.permissions import BasePermission
from .models import has_min_access

class HasMinAccessLevel(BasePermission):
    """
    Usage:
        permission_classes = [HasMinAccessLevel.with_level("admin")]
    """
    required_level = None

    def has_permission(self, request, view):
        user_access = getattr(request.user, "access_level", None)
        return has_min_access(user_access, self.required_level)

    @classmethod
    def with_level(cls, level: str):
        class _Perm(cls):
            required_level = level
        return _Perm
