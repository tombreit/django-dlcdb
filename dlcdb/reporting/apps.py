# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportingConfig(AppConfig):
    name = "dlcdb.reporting"
    verbose_name = _("Reporting")
