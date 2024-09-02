# Generated by Django 5.0.8 on 2024-09-02 16:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_alter_inventory_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='record',
            name='room',
            field=models.ForeignKey(blank=True, limit_choices_to={'deleted_at__isnull': False}, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.room', verbose_name='Room'),
        ),
    ]