from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'dlcdb.core'
    verbose_name = "DLCDB Core"

    nav_entries = [
        {
            'slot': 'nav_main',
            'order': 1,
            'label': 'Verleih',
            'icon': 'fa-solid fa-arrow-right-arrow-left',
            'url': 'admin:core_lentrecord_changelist',
            'required_permission': 'view_lentrecord',
        },
        {
            'slot': 'nav_main',
            'order': 2,
            'label': 'Devices',
            'icon': 'fa-solid fa-barcode',
            'url': 'admin:core_device_changelist',
            'required_permission': 'view_device',
        },
        {
            'slot': 'nav_main',
            'order': 4,
            'label': 'Lizenzen',
            'icon': 'fa-solid fa-scale-balanced',
            'url': 'admin:core_licencerecord_changelist',
            'required_permission': 'view_licencerecord',
        },
        # ... additional entries as needed
    ]
