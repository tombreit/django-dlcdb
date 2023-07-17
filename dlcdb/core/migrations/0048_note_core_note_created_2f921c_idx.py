# Generated by Django 4.2.3 on 2023-07-17 21:37

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0047_alter_note_inventory"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="note",
            index=models.Index(fields=["created_at", "inventory"], name="core_note_created_2f921c_idx"),
        ),
    ]
