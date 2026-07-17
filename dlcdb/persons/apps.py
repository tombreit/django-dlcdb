# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PersonsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.persons"
    verbose_name = _("Persons")
