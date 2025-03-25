# Generated by Django 5.1.5 on 2025-03-06 17:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0005_alter_subscription_managers'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='message',
            name='subscription',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='device',
        ),
        migrations.RemoveField(
            model_name='subscription',
            name='subscriber',
        ),
        migrations.DeleteModel(
            name='HistoricalSubscription',
        ),
        migrations.DeleteModel(
            name='Message',
        ),
        migrations.DeleteModel(
            name='Subscription',
        ),
    ]
