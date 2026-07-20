# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dlcdb.core.utils.helpers import get_contact_email
from dlcdb.organization.models import Branding
from dlcdb.theme.context_processors import project_meta


def email_footer_context(tenant=None) -> dict:
    """
    Context needed by the shared emails/email_footer.txt include.

    ``contact_email`` is resolved via the shared fallback chain (tenant ->
    Branding IT dept email -> DEFAULT_FROM_EMAIL); pass ``tenant`` where the
    mail is scoped to one (e.g. per-tenant overdue reminders).
    """
    return {
        "branding": Branding.load(),
        "project_version": project_meta(None)["project_version"],
        "contact_email": get_contact_email(tenant),
    }
