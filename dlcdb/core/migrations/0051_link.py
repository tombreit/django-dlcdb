# Generated by Django 5.0.1 on 2024-02-26 11:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_room_website_alter_room_is_auto_return_room_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Link',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(blank=True, max_length=255, verbose_name='Benutzername (denormalized)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Erstellt')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='Geändert')),
                ('linktext', models.CharField(max_length=255)),
                ('url', models.URLField(blank=True)),
                ('file', models.FileField(blank=True, upload_to='links/')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Link',
                'verbose_name_plural': 'Links',
                'ordering': ['-created_at'],
            },
        ),
    ]
