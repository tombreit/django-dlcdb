# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LendingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.lending"
    verbose_name = _("Lending")

    def ready(self):
        # Register the lending device-picker source with the shared theme registry.
        from . import pickers

        pickers.register()

        # The regulation pages, for the buttons next to the lending profile form's select.
        from dlcdb.core.models import Link
        from dlcdb.theme.related import RelatedPages, register_related_pages

        register_related_pages(RelatedPages(Link, "lending:regulation:edit", "lending:regulation:add"))
