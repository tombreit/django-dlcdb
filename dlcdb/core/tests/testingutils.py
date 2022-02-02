from django.test import TestCase as DjangoTestCase


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
