# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Logging handlers for ``LOGGING`` (``dlcdb/settings/base.py``)."""

from django.utils import log


class AdminEmailHandler(log.AdminEmailHandler):
    """
    Django's ``AdminEmailHandler``, which never breaks the caller.

    With ``MAILERS`` configured, Django 6.1 sends the admin mail without
    ``fail_silently``: an unreachable mail server turns every logged error,
    e.g. a request with a disallowed host, into a 500. Like any logging
    handler's own errors, a failed admin mail goes to ``handleError`` instead,
    which prints it to stderr.
    """

    def emit(self, record):
        try:
            super().emit(record)
        except Exception:
            self.handleError(record)
