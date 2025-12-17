# backend/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User,
    UserProfile,
    ProfileHistory,
    LocalChapter,
    ChapterMembership,
)



@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Custom admin for our custom User model.
    Adds access_level to the standard Django user admin.
    """

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("EMMA Access", {"fields": ("access_level",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "access_level"),
        }),
    )

    list_display = ("email", "username", "access_level", "is_staff", "is_superuser")
    list_filter = ("access_level", "is_staff", "is_superuser")
    ordering = ("email",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "access_level",
        "iq_score",
        "eq_score",
        "gq_score",
        "net_worth",
        "created_at",
        "updated_at",
    )
    list_filter = ("access_level",)
    search_fields = ("user__username", "user__email")


@admin.register(ProfileHistory)
class ProfileHistoryAdmin(admin.ModelAdmin):
    list_display = ("profile", "access_level", "snapshot_at")
    list_filter = ("access_level", "snapshot_at")
    search_fields = ("profile__user__username", "profile__user__email")


@admin.register(LocalChapter)
class LocalChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country", "city", "is_active", "created_at")
    list_filter = ("is_active", "country", "city")
    search_fields = ("name", "code", "country", "city")


@admin.register(ChapterMembership)
class ChapterMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter", "member_tier", "rating_score", "joined_at")
    list_filter = ("member_tier", "chapter")
    search_fields = ("user__username", "user__email", "chapter__name", "chapter__code")
