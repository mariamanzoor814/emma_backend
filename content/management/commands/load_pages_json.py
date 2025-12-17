import json
from pathlib import Path
from django.core.management.base import BaseCommand

from content.models import Page, ContentBlock

CONTENT_DIR = Path("content_json/pages")


class Command(BaseCommand):
    help = "Load/Update pages + blocks from JSON files in content_json/pages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--slug",
            help="Only load the JSON file matching this slug (default: global-footer)",
        )
        parser.add_argument(
            "--file",
            help="Path to a single JSON file to load (overrides --slug filter)",
        )

    def handle(self, *args, **options):
        target_slug = options.get("slug") or "global-footer"
        target_file = options.get("file")

        if target_file:
            files = [Path(target_file)]
        else:
            if not CONTENT_DIR.exists():
                self.stdout.write(self.style.ERROR(f"Folder not found: {CONTENT_DIR}"))
                return
            files = [f for f in CONTENT_DIR.glob("*.json") if f.stem == target_slug]

        if not files:
            self.stdout.write(
                self.style.WARNING(
                    f"No JSON files found for slug '{target_slug}' in {CONTENT_DIR}"
                )
            )
            return

        for f in files:
            if not f.exists():
                self.stdout.write(self.style.WARNING(f"File not found: {f}"))
                continue

            data = json.loads(f.read_text(encoding="utf-8"))
            if target_slug and data.get("slug") != target_slug:
                # Skip files whose internal slug doesn't match the requested one
                continue

            slug = data["slug"]
            template = data.get("template", "content")
            blocks_data = data.get("blocks", [])

            page, _ = Page.objects.update_or_create(
                slug=slug,
                defaults={"template": template},
            )

            page.blocks.all().delete()

            # ✅ ADD THIS CHECK RIGHT HERE
            if not isinstance(blocks_data, list):
                self.stdout.write(self.style.WARNING(
                    f"Skipping blocks for {slug}: 'blocks' is not a list"
                ))
                continue

            for i, b in enumerate(blocks_data):

                # ✅ ADD THESE CHECKS INSIDE THE LOOP
                if not isinstance(b, dict):
                    self.stdout.write(self.style.WARNING(
                        f"Skipping invalid block #{i} for {slug}: not an object"
                    ))
                    continue

                key = b.get("key")
                if not key:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping block #{i} for {slug}: missing 'key'"
                    ))
                    continue

                ContentBlock.objects.create(
                    page=page,
                    key=key,  # ✅ now safe
                    language=b.get("language", "en"),
                    block_type=b.get("block_type", "text"),
                    value=b.get("value", {}),
                    sort_order=b.get("sort_order", i),  # better default ordering
                )

            self.stdout.write(self.style.SUCCESS(f"Loaded page: {slug}"))

        self.stdout.write(self.style.SUCCESS("All pages loaded successfully"))
