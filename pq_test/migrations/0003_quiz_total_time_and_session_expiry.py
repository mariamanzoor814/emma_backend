from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pq_test", "0002_quizsession_is_public_quizsession_join_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="quiz",
            name="total_time_limit_seconds",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Optional total time limit for the whole quiz in seconds; 0 = no limit.",
            ),
        ),
        migrations.AddField(
            model_name="quizsession",
            name="total_time_expires_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="When the total quiz time ends for everyone.",
            ),
        ),
        migrations.AddField(
            model_name="quizsession",
            name="total_time_limit_seconds",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Copied from quiz on start; 0 = no total limit.",
            ),
        ),
        migrations.AddField(
            model_name="participantsession",
            name="completed_reason",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="participantsession",
            name="not_done_questions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
