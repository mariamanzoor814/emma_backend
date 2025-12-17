# backend/navigation/models.py
from django.db import models
from accounts.models import AccessLevel


class MenuItem(models.Model):
    POSITION_TOP = "top"
    POSITION_MAIN = "main"
    POSITION_FOOTER = "footer"

    POSITION_CHOICES = [
        (POSITION_TOP, "Top"),
        (POSITION_MAIN, "Main"),
        (POSITION_FOOTER, "Footer"),
    ]

    title_key = models.CharField(
        max_length=255,
        help_text="Translation key, e.g. 'menu.about.mission' (NO hardcoded text).",
    )
    slug = models.SlugField(
        max_length=255,
        blank=True,
        help_text="Optionally used to map to a content page slug.",
    )
    path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Route or external URL, e.g. '/about' or 'https://emmafoundation.net'.",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    position = models.CharField(
        max_length=20,
        choices=POSITION_CHOICES,
        default=POSITION_MAIN,
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    open_in_new_tab = models.BooleanField(default=False)


    access_level = models.CharField(
    max_length=32,
    choices=AccessLevel.choices,
    blank=True,
    null=True,
    help_text="If empty: visible to everyone. Else: restricted."
)


    class Meta:
        ordering = ["position", "order"]
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"

    def __str__(self) -> str:
        return f"{self.title_key} ({self.position})"
