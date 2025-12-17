# backend/content/admin.py
from django.contrib import admin

from .models import ContentBlock, Page


class ContentBlockInline(admin.TabularInline):
    model = ContentBlock
    extra = 1
    fields = ("key", "language", "block_type", "value", "image", "sort_order")



@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("id", "slug", "template", "is_active")
    list_filter = ("is_active", "template")
    search_fields = ("slug",)
    # filter_horizontal = ("access_levels",)
    inlines = [ContentBlockInline]


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "page", "key", "language", "block_type", "sort_order")
    list_filter = ("language", "block_type")
    search_fields = ("key", "page__slug")
    ordering = ("page", "sort_order", "key")
    fields = ("page", "key", "language", "block_type", "value", "image", "sort_order")
