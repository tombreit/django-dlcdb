# Generated by Django 5.0.2 on 2024-04-09 09:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_link'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='inventory',
            options={'verbose_name': 'Inventory', 'verbose_name_plural': 'Inventories'},
        ),
    ]