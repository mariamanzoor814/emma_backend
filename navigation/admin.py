from django.contrib import admin

from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title_key", "position", "order", "is_active", "parent")
    list_filter = ("position", "is_active")
    search_fields = ("title_key", "slug", "path")
    ordering = ("position", "order")
    # filter_horizontal = ("access_levels",)
