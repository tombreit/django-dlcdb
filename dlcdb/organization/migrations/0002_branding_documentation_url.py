# Generated by Django 4.1.3 on 2022-11-18 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="branding",
            name="documentation_url",
            field=models.URLField(blank=True),
        ),
    ]
