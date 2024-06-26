# Generated by Django 4.0.1 on 2022-02-01 21:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_delete_inventoryroom'),
    ]

    operations = [
        # migrations.RemoveField(
        #     model_name='saplistcomparisonresult',
        #     name='sap_list',
        # ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='saplistcomparisonresult',
                    name='sap_list',
                ),
            ],
            database_operations=[],
        ),
        # migrations.DeleteModel(
        #     name='SapList',
        # ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='SapList',
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='SapList',
                    table='inventory_saplist',
                ),
            ],
        ),
        # migrations.DeleteModel(
        #     name='SapListComparisonResult',
        # ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name='SapListComparisonResult',
                ),
            ],
            database_operations=[
                migrations.AlterModelTable(
                    name='SapListComparisonResult',
                    table='inventory_saplistcomparisonresult',
                ),
            ],
        ),
    ]
