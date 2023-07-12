# Generated by Django 4.2.3 on 2023-07-11 15:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0042_note_created_by_note_updated_at_note_updated_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="record",
            name="room",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="core.room", verbose_name="Room"
            ),
        ),
    ]