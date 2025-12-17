from rest_framework import serializers
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


class TopLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopLink
        fields = ["id", "label", "href"]


class MainCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "label", "href"]


class HeroItemSerializer(serializers.ModelSerializer):
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = HeroItem
        fields = ["id", "label", "imageUrl"]

    def get_imageUrl(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return obj.image_url


class HeroSlideSerializer(serializers.ModelSerializer):
    buttonLabel = serializers.CharField(
        source="button_label", allow_blank=True
    )
    backgroundColor = serializers.CharField(
        source="background_color", allow_blank=True
    )
    items = HeroItemSerializer(many=True, read_only=True)

    class Meta:
        model = HeroSlide
        fields = [
            "id",
            "title",
            "subtitle",
            "buttonLabel",
            "backgroundColor",
            "items",
        ]



class CircleCategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="pk")
    label = serializers.CharField(source="category.label")
    href = serializers.CharField(source="category.href")
    imageUrl = serializers.SerializerMethodField()

    class Meta:
        model = CircleCategory
        fields = ["id", "label", "href", "imageUrl"]

    def get_imageUrl(self, obj):
        request = self.context.get("request")
        if obj.image:
            url = obj.image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return obj.image_url



class ProductSerializer(serializers.ModelSerializer):
    imageUrl = serializers.SerializerMethodField()
    oldPrice = serializers.DecimalField(
        source="old_price",
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    badgeText = serializers.CharField(source="badge_text", allow_blank=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "title",
            "imageUrl",
            "price",
            "currency",
            "oldPrice",
            "badgeText",
        ]

    def get_imageUrl(self, obj):
        request = self.context.get("request")
        # Prefer uploaded image
        if obj.image:
            url = obj.image.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        # Fallback to external URL field
        return obj.image_url


class ProductSectionItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = ProductSectionItem
        fields = ["product"]


class ProductSectionSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = ProductSection
        fields = ["id", "title", "subtitle", "products"]

    def get_products(self, obj):
        from .models import Product  # to avoid circular import

        request = self.context.get("request")

        if obj.auto_fill:
            # AUTO MODE: latest active products
            qs = Product.objects.filter(is_active=True).order_by("-created_at")[
                : obj.max_products
            ]
            return ProductSerializer(qs, many=True, context=self.context).data

        # MANUAL MODE: use ProductSectionItem links
        items = obj.section_items.select_related("product").all()
        products = [item.product for item in items if item.product.is_active]
        return ProductSerializer(products, many=True, context=self.context).data


class FooterLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = FooterLink
        fields = ["id", "label", "href"]


class FooterColumnSerializer(serializers.ModelSerializer):
    links = FooterLinkSerializer(many=True, read_only=True)

    class Meta:
        model = FooterColumn
        fields = ["id", "title", "links"]
