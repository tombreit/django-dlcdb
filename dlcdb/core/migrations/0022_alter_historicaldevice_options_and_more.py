# Generated by Django 4.0.4 on 2022-05-18 08:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_device_order_number_historicaldevice_order_number'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicaldevice',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical Device', 'verbose_name_plural': 'historical Devices'},
        ),
        migrations.AlterField(
            model_name='historicaldevice',
            name='history_date',
            field=models.DateTimeField(db_index=True),
        ),
    ]
