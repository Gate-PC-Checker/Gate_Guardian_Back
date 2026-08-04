# Generated manually to add department status field.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dpts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="department",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("inactive", "Inactive"), ("suspended", "Suspended")],
                default="active",
                max_length=20,
            ),
        ),
    ]
