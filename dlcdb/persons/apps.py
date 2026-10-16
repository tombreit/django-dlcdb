# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PersonsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.persons"
    verbose_name = _("Persons")

    def ready(self):
        # The person pages, for the buttons next to the form selects.
        from dlcdb.core.models import Person
        from dlcdb.theme.related import RelatedPages, register_related_pages

        register_related_pages(RelatedPages(Person, "persons:detail", "persons:add"))
