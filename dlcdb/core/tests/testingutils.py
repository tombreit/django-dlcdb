# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.test import TestCase as DjangoTestCase


def establish_state(proxy_model, **kwargs):
    """Create a record for test setup, bypassing lifecycle transition enforcement.

    For fixtures that need a device *already* in some state (lent, lost, ...)
    without exercising the transition that would normally lead there -- the
    equivalent of data imported directly into that state. When the test is about
    the transition itself, drive the real transition instead.
    """
    record = proxy_model(**kwargs)
    record.save(check_transition=False)
    return record


class DisableMigrations(object):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"


class NoMigrationsTestCase(DjangoTestCase):
    """
    Extend your test cases from this class and migrations will be disabled.
    """

    def __init__(self, *args, **kw):
        from django.conf import settings

        settings.MIGRATION_MODULES = DisableMigrations()
        super(DjangoTestCase, self).__init__(*args, **kw)
