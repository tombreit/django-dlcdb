# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dlcdb.organization.models import Branding


def branding(request):
    """Make branding settings available for all requests."""
    branding = Branding.load()
    return {"branding": branding}
