# Generated by Django 4.1.4 on 2022-12-20 10:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("smallstuff", "0002_alter_thing_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="assignedthing",
            options={
                "ordering": ["person__last_name"],
                "verbose_name": "Issued stuff",
                "verbose_name_plural": "Issued stuff",
            },
        ),
    ]
