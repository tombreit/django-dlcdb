# Generated by Django 4.2.3 on 2023-08-11 07:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0049_alter_removerlist_file"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="website",
            field=models.URLField(
                blank=True,
                help_text="For example, a URL to a room plan. When available and applicable, room details are linked to this URL.",
            ),
        ),
        migrations.AlterField(
            model_name="room",
            name="is_auto_return_room",
            field=models.BooleanField(
                default=False,
                help_text="Returned loaned devices are automatically assigned to this room",
                verbose_name='"Auto return" room',
            ),
        ),
        migrations.AlterField(
            model_name="room",
            name="is_external",
            field=models.BooleanField(
                default=False,
                help_text="Location/room where assets are collected that cannot be located, e.g., loaned, off-site .",
                verbose_name="External/Lent Room",
            ),
        ),
    ]
