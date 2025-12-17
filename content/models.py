# backend/content/models.py
from django.db import models
from accounts.models import AccessLevel


class Page(models.Model):
    slug = models.SlugField(unique=True, max_length=255)
    template = models.CharField(max_length=100, default="default")
    is_active = models.BooleanField(default=True)

    # Single access level for now (we can expand later if you want multiple)
    access_level = models.CharField(
        max_length=32,
        choices=AccessLevel.choices,
        blank=True,
        null=True,
        help_text="If empty, public page. If set, only visible to that access level and above (we'll enforce in API).",
    )

    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"

    def __str__(self) -> str:
        return self.slug


class ContentBlock(models.Model):
    """
    A block or section of content on a page.
    Example key: 'hero.title', 'hero.subtitle', 'section1.body', etc.
    """

    TYPE_TEXT = "text"
    TYPE_MARKDOWN = "markdown"
    TYPE_HTML = "html"
    TYPE_JSON = "json"
    TYPE_IMAGE = "image"
    TYPE_LIST = "list"

    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_MARKDOWN, "Markdown"),
        (TYPE_HTML, "HTML"),
        (TYPE_JSON, "JSON"),
        (TYPE_IMAGE, "Image"),
        (TYPE_LIST, "List"),
    ]

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    key = models.CharField(
        max_length=255,
        help_text="Logical key, e.g. 'hero.title' or 'section1.body'.",
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="Language code, e.g. 'en', 'ur'.",
    )
    block_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_TEXT,
    )
    value = models.JSONField(
        null=True,
        blank=True,
        help_text="For text: {'text': '...'}, for rich structures, use JSON.",
    )

    # 🔥 New: optional image file for TYPE_IMAGE blocks
    image = models.ImageField(
        upload_to="content/blocks/",
        blank=True,
        null=True,
        help_text="Upload image for this block when block_type = image."
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("page", "key", "language")
        ordering = ["page", "sort_order", "key"]
        verbose_name = "Content Block"
        verbose_name_plural = "Content Blocks"

    def __str__(self) -> str:
        return f"{self.page.slug}:{self.key} ({self.language})"
