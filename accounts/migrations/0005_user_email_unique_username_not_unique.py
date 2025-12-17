from django.db import migrations, models
from django.core.validators import RegexValidator


def dedupe_emails(apps, schema_editor):
    """
    Ensure email values are unique before adding the DB unique constraint.
    - Blank/null emails are replaced with a deterministic placeholder using the user id.
    - Duplicate emails are kept on the first user (by id); later duplicates are suffixed with +dup<id>.
    - Emails are lowercased for consistency.
    Also backfill username if it is blank so later validations have something present.
    """
    User = apps.get_model("accounts", "User")
    db = schema_editor.connection.alias

    # Keep a simple in-memory set of already-assigned canonical emails to avoid collisions.
    seen = set()

    for user in User.objects.using(db).all().order_by("id"):
        raw_email = (user.email or "").strip()

        if raw_email:
            local, sep, domain = raw_email.partition("@")
            local = local or f"user{user.id}"
            domain = domain or "placeholder.local"
        else:
            local = f"user{user.id}"
            domain = "placeholder.local"

        base_email = f"{local}@{domain}".lower()

        if base_email in seen:
            # Append a deterministic suffix to keep uniqueness.
            candidate = f"{local}+dup{user.id}@{domain}".lower()
            bump = 1
            while candidate in seen:
                bump += 1
                candidate = f"{local}+dup{user.id}_{bump}@{domain}".lower()
            unique_email = candidate
        else:
            unique_email = base_email

        seen.add(unique_email)

        if not user.username:
            user.username = local

        # Lowercase and update.
        user.email = unique_email
        user.save(update_fields=["email", "username"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_profile_avatar_and_bio"),
    ]

    operations = [
        migrations.RunPython(dedupe_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                blank=True,
                max_length=150,
                validators=[
                    RegexValidator(
                        regex=r"^[A-Za-z0-9_-]+$",
                        message="Username can only contain letters, numbers, underscores, or hyphens.",
                    )
                ],
                verbose_name="username",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                max_length=254,
                unique=True,
                verbose_name="email address",
            ),
        ),
    ]
