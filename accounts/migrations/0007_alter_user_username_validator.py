from django.db import migrations, models
from django.core.validators import RegexValidator


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_user_username_required"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
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
    ]
