# Generated manually for company profile image support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dpts", "0002_department_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="profile_image",
            field=models.ImageField(blank=True, null=True, upload_to="departments/profile_images/"),
        ),
    ]
