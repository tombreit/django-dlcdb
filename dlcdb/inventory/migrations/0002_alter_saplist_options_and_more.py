# Generated by Django 4.0.1 on 2022-02-01 22:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='saplist',
            options={'verbose_name': 'SAP-Liste', 'verbose_name_plural': 'SAP-Listen'},
        ),
        migrations.AlterModelOptions(
            name='saplistcomparisonresult',
            options={'ordering': ('-created_at',)},
        ),
    ]
