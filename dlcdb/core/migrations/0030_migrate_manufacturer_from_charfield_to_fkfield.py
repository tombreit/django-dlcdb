# Generated by Django 4.1.3 on 2022-11-20 17:03

from django.db import migrations


def fill_manufacturer_fk(apps, schema_editor):
    Device = apps.get_model('core', 'Device')
    Manufacturer = apps.get_model('core', 'Manufacturer')
    for device in Device.objects.all():
        old_manufacturer = device.manufacturer

        if old_manufacturer is None or old_manufacturer == "":
            old_manufacturer = "unknown"

        old_manufacturer = old_manufacturer.lower()
        new_manufacturer = old_manufacturer.title()
        device.manufacturer_fk, created = Manufacturer.objects.get_or_create(name=new_manufacturer)
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_manufacturer_manufacturer_manufacturer_name_unique_and_more"),
    ]

    operations = [
        migrations.RunPython(fill_manufacturer_fk),
    ]