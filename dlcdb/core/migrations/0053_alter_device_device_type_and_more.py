# Generated by Django 5.0.8 on 2024-09-03 08:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_alter_inventory_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='device_type',
            field=models.ForeignKey(blank=True, limit_choices_to={'deleted_at__isnull': True}, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.devicetype', verbose_name='Device type'),
        ),
        migrations.AlterField(
            model_name='historicaldevice',
            name='device_type',
            field=models.ForeignKey(blank=True, db_constraint=False, limit_choices_to={'deleted_at__isnull': True}, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.devicetype', verbose_name='Device type'),
        ),
        migrations.AlterField(
            model_name='record',
            name='person',
            field=models.ForeignKey(blank=True, limit_choices_to={'deleted_at__isnull': True}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.person', verbose_name='Person'),
        ),
        migrations.AlterField(
            model_name='record',
            name='room',
            field=models.ForeignKey(blank=True, limit_choices_to={'deleted_at__isnull': True}, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.room', verbose_name='Room'),
        ),
    ]
