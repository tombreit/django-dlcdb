# Generated by Django 5.1.5 on 2025-03-25 10:04

import django.db.models.deletion
import simple_history.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0058_alter_licencerecord_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalSubscription',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('event', models.CharField(blank=True, choices=[('CONTRACT_ADDED', 'Contract Added'), ('CONTRACT_EXPIRES_SOON', 'Contract Expires Soon'), ('CONTRACT_EXPIRED', 'Contract Expired'), ('MOVED', 'Moved'), ('DEVICE_DECOMMISSIONED', 'Device decommissioned')], max_length=255, verbose_name='Type of event')),
                ('interval', models.CharField(blank=True, choices=[('point_in_time', 'Specific Date/Time'), ('immediately', 'Immediately'), ('hourly', 'Every Hour'), ('daily', 'Every Day'), ('weekly', 'Every Week'), ('monthly', 'Every Month'), ('yearly', 'Every Year')], max_length=255, verbose_name='Interval Name')),
                ('subscribed_at', models.DateTimeField(blank=True, editable=False)),
                ('is_active', models.BooleanField(default=True)),
                ('last_sent', models.DateTimeField(blank=True, null=True)),
                ('next_scheduled', models.DateTimeField(blank=True, help_text='When the next message should be sent. Based on the interval setting. Subscriptions with a date/time in the past are due for processing.', null=True)),
                ('created_at', models.DateTimeField(blank=True, editable=False)),
                ('modified_at', models.DateTimeField(blank=True, editable=False)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('device', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.device')),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('subscriber', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='core.person')),
            ],
            options={
                'verbose_name': 'historical subscription',
                'verbose_name_plural': 'historical subscriptions',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(blank=True, choices=[('CONTRACT_ADDED', 'Contract Added'), ('CONTRACT_EXPIRES_SOON', 'Contract Expires Soon'), ('CONTRACT_EXPIRED', 'Contract Expired'), ('MOVED', 'Moved'), ('DEVICE_DECOMMISSIONED', 'Device decommissioned')], max_length=255, verbose_name='Type of event')),
                ('interval', models.CharField(blank=True, choices=[('point_in_time', 'Specific Date/Time'), ('immediately', 'Immediately'), ('hourly', 'Every Hour'), ('daily', 'Every Day'), ('weekly', 'Every Week'), ('monthly', 'Every Month'), ('yearly', 'Every Year')], max_length=255, verbose_name='Interval Name')),
                ('subscribed_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('last_sent', models.DateTimeField(blank=True, null=True)),
                ('next_scheduled', models.DateTimeField(blank=True, help_text='When the next message should be sent. Based on the interval setting. Subscriptions with a date/time in the past are due for processing.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('device', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.device')),
                ('subscriber', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.person')),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('subject', models.CharField(blank=True, max_length=255)),
                ('body', models.TextField(blank=True)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notifications.subscription')),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
    ]
