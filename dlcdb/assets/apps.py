# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.assets"
    verbose_name = _("Assets")

    def ready(self):
        # Register the relocate device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()

        # The master data pages, for the buttons next to the form selects.
        from dlcdb.core.models import DeviceType, Manufacturer, Supplier
        from dlcdb.theme.related import RelatedPages, register_related_pages

        register_related_pages(RelatedPages(DeviceType, "assets:device_type:edit", "assets:device_type:add"))
        register_related_pages(RelatedPages(Manufacturer, "assets:manufacturer:edit", "assets:manufacturer:add"))
        register_related_pages(RelatedPages(Supplier, "assets:supplier:edit", "assets:supplier:add"))
