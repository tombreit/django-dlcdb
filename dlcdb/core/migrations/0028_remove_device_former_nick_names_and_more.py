# Generated by Django 4.1.3 on 2022-11-15 18:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0027_device_backup_encryption_key_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="device",
            name="former_nick_names",
        ),
        migrations.RemoveField(
            model_name="historicaldevice",
            name="former_nick_names",
        ),
    ]