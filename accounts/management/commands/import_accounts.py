import logging
from django.core.management.base import BaseCommand, CommandError

from accounts.importers import import_accounts_from_excel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import accounts, profiles, chapters, and memberships from an Excel file."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the Excel file to import")

    def handle(self, *args, **options):
        path = options["path"]
        try:
            import_accounts_from_excel(path)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Import failed")
            raise CommandError(f"Import failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Import completed for {path}"))
