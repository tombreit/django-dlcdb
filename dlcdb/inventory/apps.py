from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'dlcdb.inventory'
    verbose_name = 'DLCDB Inventory'

    nav_entries = [
        {
            'slot': 'nav_main',
            'order': 5,
            'label': 'Inventarisieren',
            'icon': 'fa-solid fa-glasses',
            'url': 'inventory:inventorize-room-list',
            'required_permission': 'true',
            'show_condition': 'active_inventory_exists',
        },
        {
            'slot': 'nav_processes',
            'order': 40,
            'label': 'Inventarisieren',
            'icon': 'fa-solid fa-glasses',
            'url': 'inventory:inventorize-room-list',
            'required_permission': 'true',
        },
        {
            'slot': 'nav_processes',
            'order': 50,
            'label': 'SAP Abgleich',
            'icon': '',
            'url': 'admin:inventory_saplist_changelist',
            'required_permission': 'true',
        },
    ]
