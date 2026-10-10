# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import itertools

from django.contrib.auth.models import Group
from django.test import TestCase

from dlcdb.core import models
from dlcdb.tenants.models import Tenant

# Running numbers for the IDs of generated test devices: both IDs are unique in
# the database, and random numbers collided now and then.
_device_numbers = itertools.count(1)


class BaseTest(TestCase):
    """
    Provides a set of useful helper functions to create data.
    """

    DEFAULT_TENANT = "Default test tenant"

    def _default_tenant(self):
        """The tenant of test devices unless a test passes its own."""
        tenant, _ = Tenant.objects.get_or_create(name=self.DEFAULT_TENANT)
        group, _ = Group.objects.get_or_create(name=self.DEFAULT_TENANT)
        tenant.groups.add(group)
        return tenant

    def _join_default_tenant(self, user):
        """
        Let ``user`` see the devices of the default test tenant. Superusers need
        it too: they see only the tenants of their groups.
        """
        self._default_tenant()
        user.groups.add(Group.objects.get(name=self.DEFAULT_TENANT))
        return user

    def _create_device(self, device_type=None, edv_id=None, sap_id=None, tenant=None):
        """
        A device of ``tenant`` (default: ``_default_tenant()``). Every device
        needs a tenant to be visible; tests about devices without tenant create
        them directly via ``Device.objects.create()``.
        """
        number = next(_device_numbers)
        device = models.Device(
            device_type=device_type or models.DeviceType.objects.get_or_create(name="Notebook", prefix="NTB")[0],
            edv_id=edv_id or f"auto-{number}",
            # A valid SAP ID (main-sub); no test uses the main number 99999 itself.
            sap_id=sap_id or f"99999-{number}",
            tenant=tenant or self._default_tenant(),
        )
        device.save()
        return device
