# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class JournalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dlcdb.journal"
    verbose_name = _("Journal")
