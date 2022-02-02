import pytest
from django.test import TestCase
from dlcdb.core import models


@pytest.mark.skip
class DuplicateFinderTestCase(TestCase):

    def test_example(self):
        a = 0
        b = 2
        self.assertNotEqual(a, b)

    def test_duplicates(self):

        dt = models.DeviceType.objects.get_or_create(name='Notebook', prefix='NTB')[0]

        # create non duplicates
        for i in range(0, 5):
            device_1 = models.Device(
                edv_id=i,
                sap_id=i,
                device_type=dt,
            )
            device_1.save()

        # create duplicates
        for i in range(0, 5):
            device_1 = models.Device(
                edv_id='d1',
                sap_id='d1',
                device_type=dt,
            )
            device_1.save()

        qs = models.Device.objects.filter(device_type=dt)
        # assert the correct number of created devices
        self.assertEqual(qs.count(), 10)
