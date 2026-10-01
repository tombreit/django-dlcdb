# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
A user whose groups belong to several tenants sees and manages the union of
these tenants, and nothing of the others.
"""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import Device, InRoomRecord, LentRecord, Person, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class MultiTenantUserTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name="Tenant A")
        cls.tenant_b = Tenant.objects.create(name="Tenant B")
        cls.foreign = Tenant.objects.create(name="Foreign tenant")

        it = Group.objects.create(name="it")
        cls.tenant_a.groups.add(it)
        cls.tenant_b.groups.add(it)
        cls.user = get_user_model().objects.create_user(username="it-staff", email="it@example.com", password="secret")
        cls.user.groups.add(it)
        cls.user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="core",
                codename__in=[
                    "view_device",
                    "add_device",
                    "change_device",
                    "view_licencerecord",
                    "view_lentrecord",
                    "transition_can_relocate_device",
                ],
            )
        )

        cls.room = Room.objects.create(number="M1.01")
        cls.device_a = cls()._create_device(edv_id="EDV-A", sap_id="1-1", tenant=cls.tenant_a)
        cls.device_b = cls()._create_device(edv_id="EDV-B", sap_id="2-2", tenant=cls.tenant_b)
        cls.device_foreign = cls()._create_device(edv_id="EDV-FOREIGN", sap_id="3-3", tenant=cls.foreign)
        for device in (cls.device_a, cls.device_b, cls.device_foreign):
            InRoomRecord.objects.create(device=device, room=cls.room)

    def setUp(self):
        self.client.force_login(self.user)

    def _lend(self, device, last_name):
        device.is_lentable = True
        device.save()
        person = Person.objects.create(first_name="Borrower", last_name=last_name)
        establish_state(
            LentRecord,
            device=device,
            person=person,
            room=self.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )
        return person

    def test_device_index_shows_the_union_with_the_tenant_column(self):
        response = self.client.get(reverse("assets:device_index"))

        self.assertContains(response, "EDV-A")
        self.assertContains(response, "EDV-B")
        self.assertNotContains(response, "EDV-FOREIGN")
        self.assertContains(response, "ordering=tenant")

    def test_add_form_requires_a_choice_among_own_tenants(self):
        url = reverse("assets:device_add")

        tenant_field = self.client.get(url).context["form"].fields["tenant"]
        self.assertEqual(set(tenant_field.queryset), {self.tenant_a, self.tenant_b})
        self.assertIsNone(tenant_field.initial)

        missing = self.client.post(url, {"edv_id": "EDV-NEW", "sap_id": "4-4"})
        self.assertIn("tenant", missing.context["form"].errors)
        foreign = self.client.post(url, {"edv_id": "EDV-NEW", "sap_id": "4-4", "tenant": self.foreign.pk})
        self.assertIn("tenant", foreign.context["form"].errors)

        self.client.post(url, {"edv_id": "EDV-NEW", "sap_id": "4-4", "tenant": self.tenant_b.pk})
        self.assertEqual(Device.objects.get(edv_id="EDV-NEW").tenant, self.tenant_b)

    def test_device_moves_between_own_tenants_on_the_detail_page(self):
        url = reverse("assets:device_detail", args=[self.device_a.pk])
        form = self.client.get(url).context["form"]
        payload = {name: (form[name].value() or "") for name in form.fields}

        foreign = self.client.post(url, {**payload, "tenant": self.foreign.pk})
        self.assertIn("tenant", foreign.context["form"].errors)

        self.client.post(url, {**payload, "tenant": self.tenant_b.pk})
        self.device_a.refresh_from_db()
        self.assertEqual(self.device_a.tenant, self.tenant_b)

    def test_admin_relocate_action_moves_between_own_tenants(self):
        url = f"{reverse('core:core_devices_relocate')}?ids={self.device_a.pk}"
        payload = {"devices": [self.device_a.pk], "device_ids": [self.device_a.pk]}

        tenant_field = self.client.get(url).context["form"].fields["new_tenant"]
        self.assertEqual(set(tenant_field.queryset), {self.tenant_a, self.tenant_b})

        self.client.post(url, {**payload, "new_tenant": self.tenant_b.pk})
        self.device_a.refresh_from_db()
        self.assertEqual(self.device_a.tenant, self.tenant_b)

    def test_dashboard_licences_and_lending_show_the_union(self):
        own_borrower = self._lend(self.device_b, "Own")
        foreign_borrower = self._lend(self.device_foreign, "Foreign")
        licence = self._create_device(sap_id="LIC-A", tenant=self.tenant_a)
        licence.is_licence = True
        licence.series = "Suite A"
        licence.save()
        InRoomRecord.objects.create(device=licence, room=self.room)
        foreign_licence = self._create_device(sap_id="LIC-F", tenant=self.foreign)
        foreign_licence.is_licence = True
        foreign_licence.series = "Suite Foreign"
        foreign_licence.save()
        InRoomRecord.objects.create(device=foreign_licence, room=self.room)

        tiles = self.client.get(reverse("dashboard:index")).context["tiles"]
        device_count = next(tile["count"] for tile in tiles if tile["url"] == "assets:device_index")
        self.assertEqual(device_count, Device.objects.filter(tenant__in=[self.tenant_a, self.tenant_b]).count())

        licences = self.client.get(reverse("licenses:index"))
        self.assertContains(licences, "Suite A")
        self.assertNotContains(licences, "Suite Foreign")

        borrowers = self.client.get(reverse("lending:index")).context["filter"].form.fields["person"].queryset
        self.assertIn(own_borrower, borrowers)
        self.assertNotIn(foreign_borrower, borrowers)
