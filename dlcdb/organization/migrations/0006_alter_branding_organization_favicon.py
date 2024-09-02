# Generated by Django 5.0.8 on 2024-09-02 08:20

import dlcdb.organization.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0005_alter_branding_organization_abbr'),
    ]

    operations = [
        migrations.AlterField(
            model_name='branding',
            name='organization_favicon',
            field=models.FileField(blank=True, null=True, upload_to='branding/', validators=[dlcdb.organization.models.validate_favicon_file_extension], verbose_name='Favicon file'),
        ),
    ]
