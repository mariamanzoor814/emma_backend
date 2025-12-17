from django.contrib import admin
from .models import (
    TopLink,
    Category,
    Product,
    HeroSlide,
    HeroItem,
    PromoConfig,
    CircleCategory,
    ProductSection,
    ProductSectionItem,
    FooterColumn,
    FooterLink,
)


@admin.register(TopLink)
class TopLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "href", "order")
    list_editable = ("href", "order")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("label", "slug", "href", "order")
    list_editable = ("href", "order")
    prepopulated_fields = {"slug": ("label",)}
    search_fields = ("label", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "currency", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("title", "short_description")
    list_editable = ("price", "is_active")


class HeroItemInline(admin.TabularInline):
    model = HeroItem
    extra = 1


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "background_color", "order", "is_active")
    list_editable = ("background_color", "order", "is_active")
    inlines = [HeroItemInline]


@admin.register(PromoConfig)
class PromoConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "button_label")


@admin.register(CircleCategory)
class CircleCategoryAdmin(admin.ModelAdmin):
    list_display = ("category", "order")
    list_editable = ("order",)


class ProductSectionItemInline(admin.TabularInline):
    model = ProductSectionItem
    extra = 1


@admin.register(ProductSection)
class ProductSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")
    inlines = [ProductSectionItemInline]


class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 2


@admin.register(FooterColumn)
class FooterColumnAdmin(admin.ModelAdmin):
    list_display = ("title", "order")
    list_editable = ("order",)
    inlines = [FooterLinkInline]
