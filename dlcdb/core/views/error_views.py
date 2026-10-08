# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth.decorators import user_passes_test


def is_superuser(user):
    return user.is_superuser


@user_passes_test(is_superuser)
def raise_test_error(request):
    """Fail on purpose, to check that unhandled errors reach the ADMINS by mail."""
    raise RuntimeError("Test error, raised on purpose via /_500/")
