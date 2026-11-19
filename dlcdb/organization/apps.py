# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrganizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.organization"
    verbose_name = _("Organization")

    def ready(self):
        # The unit and position pages, for the buttons next to the person form's selects.
        from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit
        from dlcdb.theme.related import RelatedPages, register_related_pages

        register_related_pages(RelatedPages(OrganizationalUnit, "organization:unit_detail", "organization:unit_add"))
        register_related_pages(
            RelatedPages(OrganizationalPosition, "organization:position_detail", "organization:position_add")
        )
