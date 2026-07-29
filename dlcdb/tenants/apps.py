# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.tenants"
    verbose_name = _("Tenants")
