import datetime

from django.core.management.base import BaseCommand

from dlcdb.core.utils.udb import import_udb_persons

class Command(BaseCommand):
    help = 'Import persons from an UDB instance.'

    def handle(self, *args, **kwargs):
        import_udb_persons()
