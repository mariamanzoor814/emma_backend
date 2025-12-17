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
        if instance.block_type == ContentBlock.TYPE_IMAGE and instance.image:
            request = self.context.get("request")
            url = instance.image.url
            if request is not None:
                # Build absolute URL: https://domain.com/media/...
                url = request.build_absolute_uri(url)

            value = data.get("value") or {}
            # put URL into value.url so frontend keeps working as-is
            value["url"] = url
            # keep existing alt if present, or leave empty string
            if "alt" not in value:
                value["alt"] = ""
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