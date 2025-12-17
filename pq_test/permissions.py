# backend/pq_test/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission:
    - SAFE methods (GET, HEAD, OPTIONS) allowed for everyone who can see it.
    - Write operations only allowed to obj.owner or staff.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(obj, "owner_id", None) == user.id or user.is_staff or user.is_superuser


class IsOwnerOrHostOrReadOnly(BasePermission):
    """
    Extended version for Quiz where a host of any session for the quiz
    is also allowed to modify/delete.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(obj, "owner_id", None) == user.id or user.is_staff or user.is_superuser:
            return True
        # If the object has related sessions, allow hosts of those sessions
        try:
            return obj.sessions.filter(host=user).exists()
        except Exception:
            return False


class IsHostOrReadOnly(BasePermission):
    """
    Object-level permission for QuizSession:
    Only host (or staff) can modify or control.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return getattr(obj, "host_id", None) == user.id or user.is_staff or user.is_superuser


class IsSelfParticipant(BasePermission):
    """
    For detailed result endpoints:
    Only the participant's own user can access their participant session & answers.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # ParticipantSession
        if hasattr(obj, "user_id"):
            return obj.user_id == user.id or user.is_staff or user.is_superuser

        # AnswerRecord
        if hasattr(obj, "participant"):
            participant = obj.participant
            return participant.user_id == user.id or user.is_staff or user.is_superuser

        return False
