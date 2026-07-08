# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.tenants.models import Tenant
from dlcdb.core.models import Person, LentRecord, InRoomRecord, Room
from dlcdb.core.tests import basetest


# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class NonSuperuserDeviceAdminTests(basetest.BaseTest):
    """
    Regression tests for the admin change form of a lent device edited by a
    non-superuser: `is_lentable` is readonly in this case and must not be
    part of the ModelForm, otherwise the missing checkbox value would reset
    it to False on save.
    """

    def setUp(self):
        group = Group.objects.create(name="it-department")

        self.tenant = Tenant.objects.create(name="IT")
        self.tenant.groups.add(group)

        self.user = get_user_model().objects.create_user(
            email="staffuser@example.org",
            password="secret",
            is_staff=True,
        )
        self.user.groups.add(group)
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=["view_device", "change_device"]))

        # sap_id must satisfy the "mainnumber-subnumber" form validation
        self.device = self._create_device(sap_id="12345-0")
        self.device.is_lentable = True
        self.device.tenant = self.tenant
        self.device.save()

        room = Room.objects.create(number="123")
        InRoomRecord.objects.create(device=self.device, room=room)

        person = Person.objects.create(first_name="Max", last_name="Mustermann")
        LentRecord.objects.create(device=self.device, person=person, room=room)

        self.client.force_login(self.user)

    def test_is_lentable_not_in_form_for_non_superuser_on_lent_device(self):
        change_url = reverse("admin:core_device_change", args=[self.device.pk])
        response = self.client.get(change_url)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("is_lentable", response.context["adminform"].form.fields)

    def test_note_edit_does_not_reset_is_lentable(self):
        change_url = reverse("admin:core_device_change", args=[self.device.pk])
        response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)

        # Re-submit the form as rendered, only changing the note. Fields
        # rendered as readonly (like is_lentable) have no input element in
        # the HTML, so a browser omits them from the POST data - even if the
        # ModelForm (erroneously) still contains them.
        adminform = response.context["adminform"]
        rendered_readonly = set(adminform.readonly_fields)
        data = {}
        for bound_field in adminform.form:
            if bound_field.name in rendered_readonly:
                continue
            value = bound_field.value()
            if value is False:
                continue
            elif value is True:
                value = "on"
            elif value is None:
                value = ""
            data[bound_field.html_name] = value
        data["note"] = "note updated by non-superuser"

        response = self.client.post(change_url, data)
        form_errors = response.context["adminform"].form.errors if response.status_code == 200 else None
        self.assertEqual(response.status_code, 302, form_errors)

        self.device.refresh_from_db()
        self.assertEqual(self.device.note, "note updated by non-superuser")
        self.assertTrue(self.device.is_lentable)
