# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import re

from django.template import Origin, TemplateSyntaxError
from django.template.loaders.base import Loader as BaseLoader


# Matches template names like "lending/db/42.html"
DB_TEMPLATE_RE = re.compile(r"^lending/db/(\d+)\.html$")


class DatabaseLoader(BaseLoader):
    """
    Template loader that serves LendingProfile.lent_sheet_template content
    for template names matching 'lending/db/<pk>.html'.
    """

    def get_template_sources(self, template_name):
        match = DB_TEMPLATE_RE.match(template_name)
        if match:
            yield Origin(
                name=match.group(1),
                template_name=template_name,
                loader=self,
            )

    def get_contents(self, origin):
        from .models import LendingProfile

        try:
            profile = LendingProfile.objects.get(pk=int(origin.name))
        except LendingProfile.DoesNotExist:
            raise TemplateSyntaxError(f"LendingProfile with pk={origin.name} does not exist.")

        if not profile.lent_sheet_template:
            raise TemplateSyntaxError(f"LendingProfile '{profile}' has an empty lent_sheet_template.")

        return profile.lent_sheet_template
