# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DataexchangeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.dataexchange"
    verbose_name = _("Data exchange")
