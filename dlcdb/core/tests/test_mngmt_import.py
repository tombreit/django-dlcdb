import pytest
from django.core.management import call_command
from dlcdb.core.tests import basetest


@pytest.mark.skip
class MngmtImportTest(basetest.BaseTest):
    def test(self):
        call_command('import_management_csv')
