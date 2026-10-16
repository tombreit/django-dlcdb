# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RoomsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.rooms"
    verbose_name = _("Rooms")

    def ready(self):
        # The room pages, for the buttons next to the form selects.
        from dlcdb.core.models import Room
        from dlcdb.theme.related import RelatedPages, register_related_pages

        register_related_pages(RelatedPages(Room, "rooms:detail", "rooms:add"))
