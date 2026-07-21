# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Device frontend."""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone

from dlcdb.assets.forms import DeviceForm
from dlcdb.core.models import Device, InRoomRecord, LentRecord, Manufacturer, Person, Room
from dlcdb.core.tests.basetest import BaseTest
from dlcdb.tenants.models import Tenant


_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DeviceFrontendTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.room = Room.objects.create(number="A1.01")
        cls.manufacturer = Manufacturer.objects.create(name="Example Computers")

        cls.inroom_device = cls()._create_device(edv_id="EDV-AVAILABLE", sap_id="1-1")
        cls.inroom_device.manufacturer = cls.manufacturer
        cls.inroom_device.series = "Notebook One"
        cls.inroom_device.is_lentable = True
        cls.inroom_device.save()
        InRoomRecord.objects.create(device=cls.inroom_device, room=cls.room)

        cls.untracked_device = cls()._create_device(edv_id="EDV-NO-RECORD", sap_id="2-2")

        cls.duplicate_one = cls()._create_device(edv_id="EDV-DUP-1", sap_id="3-3")
        cls.duplicate_one.serial_number = "duplicate-serial"
        cls.duplicate_one.save()
        cls.duplicate_two = cls()._create_device(edv_id="EDV-DUP-2", sap_id="4-4")
        cls.duplicate_two.serial_number = "duplicate-serial"
        cls.duplicate_two.save()

    def setUp(self):
        self.client.force_login(self.user)
        self.index_url = reverse("assets:device_index")

    def test_index_renders_device_table_and_mobile_state(self):
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<table")
        self.assertContains(response, "EDV-AVAILABLE")
        self.assertContains(response, "In room")
        self.assertContains(response, "Add device")

    def test_index_htmx_response_is_fragment_only(self):
        response = self.client.get(self.index_url, headers={"HX-Request": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="device-list"')
        self.assertNotContains(response, "<html")

    def test_search_and_state_filters(self):
        response = self.client.get(self.index_url, {"search": "Notebook One"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-AVAILABLE")
        self.assertNotContains(response, "EDV-NO-RECORD")

        response = self.client.get(self.index_url, {"state": "no-record"}, headers={"HX-Request": "true"})
        self.assertContains(response, "EDV-NO-RECORD")
        self.assertNotContains(response, "EDV-AVAILABLE")

    def test_duplicate_serial_filter_uses_the_visible_queryset(self):
        response = self.client.get(
            self.index_url,
            {"duplicate": "serial_number"},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "EDV-DUP-1")
        self.assertContains(response, "EDV-DUP-2")
        self.assertNotContains(response, "EDV-AVAILABLE")

    def test_create_device_redirects_to_its_detail_page(self):
        response = self.client.post(
            reverse("assets:device_add"),
            {"edv_id": "EDV-NEW", "sap_id": "5-5", "is_lentable": "on"},
        )

        device = Device.objects.get(edv_id="EDV-NEW")
        self.assertRedirects(response, reverse("assets:device_detail", args=[device.pk]))
        self.assertEqual(device.user, self.user)
        self.assertTrue(device.is_lentable)

    def test_non_superuser_cannot_change_loanability_while_device_is_lent(self):
        device = self._create_device(edv_id="EDV-LENT", sap_id="6-6")
        device.is_lentable = True
        device.save()
        LentRecord.objects.create(
            device=device,
            room=self.room,
            person=Person.objects.create(first_name="Max", last_name="Mustermann"),
        )
        user = get_user_model().objects.create_user(
            username="device-operator",
            email="operator@example.com",
            password="secret",
        )
        request = RequestFactory().post("/")
        request.user = user

        form = DeviceForm(
            {"edv_id": device.edv_id, "sap_id": device.sap_id},
            instance=device,
            request=request,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("is_lentable", form.errors)

    def test_tenant_field_is_shown_but_disabled_for_non_superuser(self):
        """Non-superusers always see the tenant field, but it is locked."""
        tenant = Tenant.objects.create(name="Tenant One")
        device = self._create_device(edv_id="EDV-TEN", sap_id="7-1")
        device.tenant = tenant
        device.save()

        operator = get_user_model().objects.create_user(
            username="ten-operator", email="ten-op@example.com", password="secret"
        )
        request = RequestFactory().get("/")
        request.user = operator

        form = DeviceForm(instance=device, request=request)
        tenant_field = form.fields["tenant"]
        # Present (not popped) and locked / optional.
        self.assertTrue(tenant_field.disabled)
        self.assertFalse(tenant_field.required)
        # The disabled <select> lists only the device's own tenant, and the
        # rendered control carries the HTML `disabled` attribute.
        self.assertEqual(list(tenant_field.queryset), [tenant])
        html = str(form["tenant"])
        self.assertIn("disabled", html)
        self.assertIn(str(tenant), html)

    def test_tenant_field_is_editable_for_superuser(self):
        request = RequestFactory().get("/")
        request.user = self.user  # superuser (see setUpTestData)

        form = DeviceForm(instance=self.inroom_device, request=request)
        tenant_field = form.fields["tenant"]
        self.assertFalse(tenant_field.disabled)
        self.assertFalse(tenant_field.required)
        self.assertNotIn("disabled", str(form["tenant"]))

    def test_non_superuser_cannot_reassign_tenant_via_crafted_post(self):
        """A crafted tenant in POST is ignored; the disabled field keeps the instance value."""
        own = Tenant.objects.create(name="Tenant Own")
        other = Tenant.objects.create(name="Tenant Other")
        device = self._create_device(edv_id="EDV-TEN2", sap_id="7-2")
        device.tenant = own
        device.save()

        operator = get_user_model().objects.create_user(
            username="ten-operator2", email="ten-op2@example.com", password="secret"
        )
        request = RequestFactory().post("/")
        request.user = operator

        form = DeviceForm(
            {"edv_id": device.edv_id, "sap_id": device.sap_id, "tenant": other.pk},
            instance=device,
            request=request,
        )
        self.assertTrue(form.is_valid(), form.errors)
        # The disabled field ignores the crafted `other` and keeps the instance's tenant.
        self.assertEqual(form.cleaned_data["tenant"], own)

    def test_index_paginates_and_preserves_active_filter(self):
        for i in range(30):
            self._create_device(edv_id=f"PAGED-{i:02d}", sap_id=f"9-{i}")

        # 30 matches over a 25-per-page window -> the pager is rendered...
        first = self.client.get(self.index_url, {"search": "PAGED"})
        self.assertContains(first, 'class="pagination')

        # ...and page 2's links keep the active search so paging stays filtered.
        second = self.client.get(self.index_url, {"search": "PAGED", "page": 2})
        self.assertEqual(second.status_code, 200)
        self.assertContains(second, "search=PAGED")

    def test_show_all_override_bypasses_pagination(self):
        for i in range(30):
            self._create_device(edv_id=f"PAGED-{i:02d}", sap_id=f"9-{i}")

        # Default: paginated -> numbered pager plus a "show all" link carrying the flag.
        default = self.client.get(self.index_url, {"search": "PAGED"})
        self.assertContains(default, 'class="pagination')
        self.assertContains(default, "show_all=1")

        # ?show_all=1: every match on one page, the numbered pager gone, and the
        # active search preserved on the "back to paginated" link.
        every = self.client.get(self.index_url, {"search": "PAGED", "show_all": "1"})
        self.assertEqual(every.status_code, 200)
        # The numbered pager is gone. Its nav is the unambiguous marker: the
        # "show all"/"paginated view" toggle intentionally reuses .pagination
        # pill styling, so a bare `class="pagination"` check would false-positive.
        self.assertNotContains(every, 'aria-label="List pages"')
        self.assertEqual(every.context["page_obj"].paginator.count, 30)
        self.assertEqual(len(every.context["page_obj"].object_list), 30)
        self.assertContains(every, "search=PAGED")

    def _tenant_viewer(self):
        """A non-superuser scoped to a tenant, able to view but not change devices."""
        group = Group.objects.create(name="tenant-viewers")
        tenant = Tenant.objects.create(name="Tenant One")
        tenant.groups.add(group)
        user = get_user_model().objects.create_user(username="viewer", email="viewer@example.com", password="secret")
        user.groups.add(group)
        user.user_permissions.add(Permission.objects.get(codename="view_device", content_type__app_label="core"))
        return user, tenant

    def test_view_only_user_gets_readonly_detail_and_cannot_post(self):
        user, tenant = self._tenant_viewer()
        device = self._create_device(edv_id="EDV-TENANT", sap_id="7-7")
        device.tenant = tenant
        device.save()

        self.client.force_login(user)
        url = reverse("assets:device_detail", args=[device.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<form method="post"')
        self.assertNotContains(response, 'name="machine_encryption_key"')

        # A viewer may not edit: POST is denied outright.
        denied = self.client.post(url, {"edv_id": "EDV-TENANT", "sap_id": "7-7"})
        self.assertEqual(denied.status_code, 403)

    def test_device_outside_the_users_tenant_is_404(self):
        user, _tenant = self._tenant_viewer()
        # Untenanted device: invisible to a tenant-scoped, non-superuser viewer.
        other = self._create_device(edv_id="EDV-OTHER", sap_id="8-8")

        self.client.force_login(user)
        response = self.client.get(reverse("assets:device_detail", args=[other.pk]))
        self.assertEqual(response.status_code, 404)

    def test_detail_form_uses_person_picker_not_a_full_select(self):
        response = self.client.get(reverse("assets:device_detail", args=[self.inroom_device.pk]))
        # The heavy <select> of every Person is gone; a hidden field + live-search
        # picker takes its place.
        self.assertNotContains(response, '<select name="contact_person_internal"')
        self.assertContains(response, 'type="hidden" name="contact_person_internal"')
        self.assertContains(response, 'id="contact_person-picker"')
        # Guard against a template comment leaking into the page (a multi-line
        # {# #} does not comment in Django and renders verbatim).
        self.assertNotContains(response, "result-swap region")

    def test_person_search_returns_matches_only_for_a_query(self):
        person = Person.objects.create(first_name="Erika", last_name="Musterfrau")
        url = reverse("assets:person_search")

        empty = self.client.post(url, {"q_person": ""}, headers={"HX-Request": "true"})
        self.assertNotContains(empty, "Musterfrau")

        hit = self.client.post(url, {"q_person": "Muster"}, headers={"HX-Request": "true"})
        self.assertContains(hit, "Musterfrau")
        self.assertContains(hit, f'data-option-id="{person.pk}"')

    def test_index_row_has_no_action_column_and_links_to_detail(self):
        response = self.client.get(self.index_url)

        self.assertNotContains(response, "bi-pencil")
        self.assertNotContains(response, "Open device")
        self.assertContains(response, f'href="{reverse("assets:device_detail", args=[self.inroom_device.pk])}"')

    def test_tenant_column_is_superuser_only(self):
        # The Tenant header's sort link is the unambiguous marker for the column
        # (plain "Tenant" text can otherwise appear elsewhere, e.g. the navbar).
        superuser_response = self.client.get(self.index_url)
        self.assertContains(superuser_response, "ordering=tenant")

        viewer, _tenant = self._tenant_viewer()
        self.client.force_login(viewer)
        viewer_response = self.client.get(self.index_url)
        self.assertNotContains(viewer_response, "ordering=tenant")

    def test_modified_column_uses_naturaltime_for_recent_edits_only(self):
        # A device modified "just now" renders as "now", not "... ago", so give
        # the recent device an age that is unambiguously inside the cutoff.
        # auto_now overrides a plain .save(), so backdate via .update().
        recent = self._create_device(edv_id="EDV-RECENT", sap_id="9-9")
        Device.objects.filter(pk=recent.pk).update(modified_at=timezone.now() - datetime.timedelta(hours=2))
        old = self._create_device(edv_id="EDV-OLD", sap_id="9-8")
        old_modified_at = timezone.now() - datetime.timedelta(weeks=10)
        Device.objects.filter(pk=old.pk).update(modified_at=old_modified_at)

        response = self.client.get(self.index_url)
        content = response.content.decode()

        self.assertIn("ago", content)  # EDV-RECENT's naturaltime rendering
        self.assertIn(old_modified_at.strftime("%Y-%m-%d"), content)

    def test_more_filters_toggle_is_collapsed_by_default(self):
        response = self.client.get(self.index_url)

        self.assertContains(response, "More filters")
        self.assertContains(response, 'aria-expanded="false"')
        self.assertNotContains(response, "collapse show")

    def test_more_filters_expands_when_a_secondary_filter_is_active(self):
        response = self.client.get(self.index_url, {"duplicate": "serial_number"})

        self.assertContains(response, 'aria-expanded="true"')
        self.assertContains(response, "collapse show")
