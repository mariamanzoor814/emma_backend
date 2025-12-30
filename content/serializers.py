# backend/content/serializers.py
from rest_framework import serializers

from .models import ContentBlock, Page


class ContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        fields = ["id", "key", "language", "block_type", "value", "sort_order"]
        # we don't need to expose "image" directly to frontend
        # we'll inject its URL into value in to_representation

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Only for image blocks
        if instance.block_type == ContentBlock.TYPE_IMAGE:
            value = data.get("value") or {}

            if instance.image:
                # Use uploaded image if exists
                url = instance.image.url
                request = self.context.get("request")
                if request:
                    url = request.build_absolute_uri(url)
                value["url"] = url
            else:
                # fallback for old JSON path (media/... → S3 URL)
                old_url = value.get("url", "")
                if old_url.startswith("media/"):
                    from django.conf import settings
                    value["url"] = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{old_url}"
                else:
                    value["url"] = old_url

            # ensure alt is always present
            value.setdefault("alt", "")
            data["value"] = value

        return data


class PageDetailSerializer(serializers.ModelSerializer):
    blocks = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "slug", "template", "blocks"]

    def get_blocks(self, obj):
        language = self.context.get("language", "en")
        blocks_qs = obj.blocks.filter(language=language).order_by("sort_order", "key")
        # 🔥 Pass down same context (including request) to block serializer
        return ContentBlockSerializer(blocks_qs, many=True, context=self.context).data
