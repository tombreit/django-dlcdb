# Generated by Django 4.2.3 on 2023-07-19 20:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organization", "0003_alter_branding_documentation_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="branding",
            name="room_plan",
            field=models.FileField(blank=True, null=True, upload_to="branding/"),
        ),
    ]
