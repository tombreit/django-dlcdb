# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dlcdb.organization.models import Branding
from dlcdb.theme.context_processors import project_meta


def email_footer_context() -> dict:
    """Context needed by the shared emails/email_footer.txt include."""
    return {
        "branding": Branding.load(),
        "project_version": project_meta(None)["project_version"],
    }
