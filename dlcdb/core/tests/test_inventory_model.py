from django.test import TestCase

from dlcdb.core import models


class InventoryTests(TestCase):

    def test_set_active_logic(self):
        """
        Ensure that an inventory which is saved as active sets all other inventories to
        inactive.
        :return:
        """

        i1 = models.Inventory(name='2016', is_active=True)
        i1.save()

        i2 = models.Inventory(name='2017', is_active=True)
        i2.save()

        # very important to requery i1 in order to get the fresh new database representation of i1.
        # Otherwise i1 is outdated as the query of the is_active manipulation does not affect existing python objects.
        i1 = models.Inventory.objects.get(id=i1.id)
        self.assertFalse(i1.is_active)
        self.assertTrue(i2.is_active)
