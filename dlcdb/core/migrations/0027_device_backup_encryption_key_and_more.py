# Generated by Django 4.1.3 on 2022-11-15 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_remove_person_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="backup_encryption_key",
            field=models.TextField(
                blank=True,
                help_text="Z.B. macOS TimeMachine Passwort für Backupfestplatte.",
                verbose_name="Passwort Backupverschlüsselung",
            ),
        ),
        migrations.AddField(
            model_name="device",
            name="machine_encryption_key",
            field=models.TextField(
                blank=True,
                help_text="Z.B. Bitlocker Recovery Key oder macOS FileVault Passwort für Systemfestplatte.",
                verbose_name="Passwort Festplattenverschlüsselung",
            ),
        ),
        migrations.AddField(
            model_name="historicaldevice",
            name="backup_encryption_key",
            field=models.TextField(
                blank=True,
                help_text="Z.B. macOS TimeMachine Passwort für Backupfestplatte.",
                verbose_name="Passwort Backupverschlüsselung",
            ),
        ),
        migrations.AddField(
            model_name="historicaldevice",
            name="machine_encryption_key",
            field=models.TextField(
                blank=True,
                help_text="Z.B. Bitlocker Recovery Key oder macOS FileVault Passwort für Systemfestplatte.",
                verbose_name="Passwort Festplattenverschlüsselung",
            ),
        ),
    ]
