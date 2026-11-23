# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SmallstuffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.smallstuff"
    verbose_name = _("Smallstuff")

    def ready(self):
        # The thing pages, for the similar names' "Use this one" link.
        from dlcdb.theme.related import RelatedPages, register_related_pages

        from .models import Thing

        register_related_pages(RelatedPages(Thing, "smallstuff:thing:edit", "smallstuff:thing:add"))
