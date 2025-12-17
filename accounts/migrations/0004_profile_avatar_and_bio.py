from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_userprofile_address_userprofile_city_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="about",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="avatars/"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="bio",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="location",
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
