from django.db import models
from django.utils.text import slugify


class TopLink(models.Model):
    """Links like: Daily Deals, Brand Outlet, Gift Cards, Help & Contact"""

    id = models.BigAutoField(primary_key=True)
    label = models.CharField(max_length=80)
    href = models.CharField(max_length=255, default="#")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.label


class Category(models.Model):
    """
    Store categories (Motors, Electronics, etc.).
    Also used for main nav strip & can be targeted from hero items, circle categories, etc.
    """

    id = models.BigAutoField(primary_key=True)
    label = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    href = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional URL for category page (e.g. /c/electronics).",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]

    def __str__(self) -> str:
        return self.label

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.label)
        super().save(*args, **kwargs)


class Product(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, null=True, blank=True)

    category = models.ForeignKey(
        Category, related_name="products", on_delete=models.CASCADE
    )

    # NEW: image file upload
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        help_text="Upload product image (or use external image URL below).",
    )

    # existing external URL (optional now)
    image_url = models.URLField(max_length=500, blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=8, default="$")
    badge_text = models.CharField(
        max_length=80, blank=True, help_text="For things like '20% off', 'Cyber deal'."
    )
    short_description = models.CharField(max_length=280, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        from django.utils.text import slugify

        if not self.slug:
            self.slug = slugify(self.title)[:280]
        super().save(*args, **kwargs)



class HeroSlide(models.Model):
    """
    Big hero banner slides (different colors + items)
    """

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    button_label = models.CharField(max_length=80, blank=True)
    background_color = models.CharField(
        max_length=16,
        default="#d4e43b",
        help_text="CSS color (e.g. #d4e43b)",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title


class HeroItem(models.Model):
    slide = models.ForeignKey(
        HeroSlide, related_name="items", on_delete=models.CASCADE
    )
    label = models.CharField(max_length=120)

    # uploadable image
    image = models.ImageField(
        upload_to="hero_items/",
        blank=True,
        null=True,
        help_text="Upload hero item image (or use external URL).",
    )
    # optional external URL if you want
    image_url = models.URLField(max_length=500, blank=True)

    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional target category when clicked.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.slide.title} – {self.label}"



class PromoConfig(models.Model):
    """
    Single row model for the dark promo band.
    Use the first (and only) instance.
    """

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    button_label = models.CharField(max_length=80, blank=True)

    class Meta:
        verbose_name = "Promo Config"
        verbose_name_plural = "Promo Config"

    def __str__(self) -> str:
        return self.title


class CircleCategory(models.Model):
    category = models.ForeignKey(
        Category,
        related_name="circle_entries",
        on_delete=models.CASCADE,
    )

    image = models.ImageField(
        upload_to="circle_categories/",
        blank=True,
        null=True,
        help_text="Upload circle icon image (or use external URL).",
    )
    image_url = models.URLField(max_length=500, blank=True)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.category.label} (circle)"



class ProductSection(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # NEW: auto mode
    auto_fill = models.BooleanField(
        default=False,
        help_text="If enabled, this row will automatically show latest active products.",
    )
    max_products = models.PositiveIntegerField(
        default=12,
        help_text="Maximum number of products to display when auto_fill is on.",
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title



class ProductSectionItem(models.Model):
    section = models.ForeignKey(
        ProductSection, related_name="section_items", on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product, related_name="section_items", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = ("section", "product")

    def __str__(self) -> str:
        return f"{self.section.title} – {self.product.title}"


class FooterColumn(models.Model):
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title


class FooterLink(models.Model):
    column = models.ForeignKey(
        FooterColumn, related_name="links", on_delete=models.CASCADE
    )
    label = models.CharField(max_length=120)
    href = models.CharField(max_length=255, default="#")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["column__order", "order", "id"]

    def __str__(self) -> str:
        return f"{self.column.title} – {self.label}"
