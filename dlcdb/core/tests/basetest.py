# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import random

from django.test import TestCase

from dlcdb.core import models


class BaseTest(TestCase):
    """
    Provides a set of useful helper functions to create data.
    """

    def _create_device(self, device_type=None, edv_id=None, sap_id=None):
        device = models.Device(
            device_type=device_type or models.DeviceType.objects.get_or_create(name="Notebook", prefix="NTB")[0],
            edv_id=edv_id or random.randint(0, 19999),
            sap_id=sap_id or random.randint(0, 19999),
        )
        device.save()
        return device
