from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # 👈 add this

from .models import (
    TopLink,
    Category,
    HeroSlide,
    PromoConfig,
    CircleCategory,
    ProductSection,
    FooterColumn,
)
from .serializers import (
    TopLinkSerializer,
    MainCategorySerializer,
    HeroSlideSerializer,
    CircleCategorySerializer,
    ProductSectionSerializer,
    FooterColumnSerializer,
)


class StorefrontAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        top_links = TopLink.objects.all()
        main_categories = Category.objects.all()
        hero_slides = HeroSlide.objects.filter(is_active=True).prefetch_related("items")
        promo = PromoConfig.objects.first()
        circle_categories = CircleCategory.objects.select_related("category").all()
        product_sections = (
            ProductSection.objects.filter(is_active=True)
            .prefetch_related("section_items__product")
            .all()
        )
        footer_columns = FooterColumn.objects.prefetch_related("links").all()

        data = {
            "topLinks": TopLinkSerializer(top_links, many=True).data,
            "mainCategories": MainCategorySerializer(main_categories, many=True).data,
            "heroSlides": HeroSlideSerializer(
                hero_slides, many=True, context={"request": request}
            ).data,
            "promo": {
                "title": promo.title if promo else "",
                "subtitle": promo.subtitle if promo else "",
                "buttonLabel": promo.button_label if promo else "",
            },
            "circleRow": {
                "title": "Gear up for the holidays",
                "subtitle": "",
                "items": CircleCategorySerializer(
                    circle_categories, many=True, context={"request": request}
                ).data,
            },
            "productSections": ProductSectionSerializer(
                product_sections, many=True, context={"request": request}
            ).data,
            "footerColumns": FooterColumnSerializer(
                footer_columns, many=True
            ).data,
        }
        return Response(data)
