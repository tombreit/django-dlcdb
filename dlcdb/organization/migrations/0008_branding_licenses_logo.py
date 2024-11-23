# Generated by Django 5.1.1 on 2024-11-22 12:21

import dlcdb.organization.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0007_alter_branding_organization_logo_black_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='branding',
            name='licenses_logo',
            field=models.FileField(blank=True, null=True, upload_to='branding/', validators=[dlcdb.organization.models.validate_logo_image_file_extension], verbose_name='Logo file for Licenses component'),
        ),
    ]