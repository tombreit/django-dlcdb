# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the dashboard's global search."""

import re

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import Device, DeviceType, InRoomRecord, Manufacturer, Person, Room
from dlcdb.dashboard.search import SEARCH_SOURCES
from dlcdb.smallstuff.models import AssignedThing, Thing
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class GlobalSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")

        cls.device_type = DeviceType.objects.create(name="Notebook", prefix="NTB")
        cls.manufacturer = Manufacturer.objects.create(name="Zebra Computers")
        cls.room = Room.objects.create(number="Z1.42", nickname="Zebra Lab")

        cls.device = Device.objects.create(
            edv_id="ZEBRA-DEVICE-1",
            sap_id="9001-1",
            series="Zebra Book",
            device_type=cls.device_type,
            manufacturer=cls.manufacturer,
        )
        InRoomRecord.objects.create(device=cls.device, room=cls.room)

        cls.licence = Device.objects.create(
            edv_id="ZEBRA-LICENCE-1",
            sap_id="9002-1",
            series="Zebra Suite",
            manufacturer=cls.manufacturer,
            is_licence=True,
        )

        cls.person = Person.objects.create(first_name="Zora", last_name="Zebrowski", email="zora.zebrowski@example.org")

        cls.thing = Thing.objects.create(name="Zebra Headset", slug="zebra-headset")
        cls.assignment = AssignedThing.objects.create(person=cls.person, thing=cls.thing)

    def setUp(self):
        self.client.force_login(self.user)

    def _search(self, term, **extra):
        return self.client.get(reverse("dashboard:index"), {"q": term}, **extra)

    def _group_keys(self, response):
        return [group["source"].key for group in response.context["groups"]]

    # --- empty / short queries ------------------------------------------

    def test_blank_query_returns_no_groups(self):
        self.assertEqual(self._search("").context["groups"], [])

    def test_single_character_query_returns_no_groups(self):
        """Below the minimum length nothing is searched, so one keystroke never scans every table."""
        self.assertEqual(self._search("z").context["groups"], [])

    def test_unmatched_query_returns_no_groups(self):
        self.assertEqual(self._search("nothingmatchesthis").context["groups"], [])

    # --- one match per source -------------------------------------------

    def test_device_is_found_and_links_to_its_frontend_detail(self):
        response = self._search("ZEBRA-DEVICE-1")
        self.assertIn("devices", self._group_keys(response))
        self.assertContains(response, reverse("assets:device_detail", args=[self.device.pk]))

    def test_person_is_found_by_name_and_by_email(self):
        for term in ("Zebrowski", "zora.zebrowski@example.org"):
            with self.subTest(term=term):
                response = self._search(term)
                self.assertIn("persons", self._group_keys(response))
                self.assertContains(response, reverse("persons:detail", args=[self.person.pk]))

    def test_room_is_found_by_number_and_nickname(self):
        for term in ("Z1.42", "Zebra Lab"):
            with self.subTest(term=term):
                response = self._search(term)
                self.assertIn("rooms", self._group_keys(response))
                self.assertContains(response, reverse("rooms:detail", args=[self.room.pk]))

    def test_smallstuff_assignment_is_found_and_links_to_its_person(self):
        response = self._search("Zebra Headset")
        self.assertIn("smallstuff", self._group_keys(response))
        self.assertContains(response, reverse("smallstuff:person_detail", args=[self.person.pk]))

    # --- group order ------------------------------------------------------

    def test_groups_appear_in_the_configured_order(self):
        """Declaration order in SEARCH_SOURCES is the display order."""
        self.assertEqual(
            [source.key for source in SEARCH_SOURCES],
            ["lendings", "devices", "licenses", "persons", "rooms", "smallstuff"],
        )

    def test_a_multi_group_result_is_rendered_in_that_order(self):
        """ "Zebra" matches a device, a room, a licence and a smallstuff assignment."""
        keys = self._group_keys(self._search("Zebra"))

        self.assertEqual(keys, ["devices", "licenses", "rooms", "smallstuff"])

    # --- licences are their own group -----------------------------------

    def test_licence_is_found_in_its_own_group_and_never_among_devices(self):
        response = self._search("ZEBRA-LICENCE-1")
        keys = self._group_keys(response)

        self.assertIn("licenses", keys)
        self.assertNotIn("devices", keys)
        # licenses:edit is routed by device pk.
        self.assertContains(response, reverse("licenses:edit", kwargs={"license_id": self.licence.pk}))

    def test_a_term_matching_both_splits_them_across_the_two_groups(self):
        """ "Zebra Computers" is the manufacturer of the device *and* of the licence."""
        response = self._search("Zebra Computers")
        groups = {group["source"].key: group for group in response.context["groups"]}

        self.assertEqual([row.pk for row in groups["devices"]["rows"]], [self.device.pk])
        self.assertEqual([row.pk for row in groups["licenses"]["rows"]], [self.licence.pk])

    # --- permissions -----------------------------------------------------

    def test_a_group_is_hidden_from_a_user_without_its_permission(self):
        """A person matches, but a user lacking core.view_person must not see the group."""
        limited = get_user_model().objects.create_user(
            username="limited", email="limited@example.com", password="secret"
        )
        limited.user_permissions.add(Permission.objects.get(codename="view_device", content_type__app_label="core"))
        self.client.force_login(limited)

        response = self._search("Zebrowski")

        self.assertNotIn("persons", self._group_keys(response))
        self.assertNotContains(response, reverse("persons:detail", args=[self.person.pk]))

    def test_a_user_without_any_relevant_permission_sees_nothing(self):
        nobody = get_user_model().objects.create_user(username="nobody", email="nobody@example.com", password="secret")
        self.client.force_login(nobody)

        self.assertEqual(self._search("Zebra").context["groups"], [])

    # --- tenant scoping ---------------------------------------------------

    def test_devices_are_scoped_to_the_requesting_users_tenant(self):
        """Tenant scoping applies to devices; the search must honour it like the device list does.

        Deliberately a non-superuser: get_current_tenant() never resolves a
        tenant for superusers, so they are the one case that is never scoped.
        """
        group = Group.objects.create(name="tenant-a-viewers")
        tenant_a = Tenant.objects.create(name="TenantA")
        tenant_a.groups.add(group)
        tenant_b = Tenant.objects.create(name="TenantB")

        own = Device.objects.create(edv_id="ZEBRA-OWN-1", sap_id="9003-1", tenant=tenant_a)
        foreign = Device.objects.create(edv_id="ZEBRA-FOREIGN-1", sap_id="9004-1", tenant=tenant_b)

        viewer = get_user_model().objects.create_user(
            username="tenant-viewer", email="viewer@example.com", password="secret"
        )
        viewer.groups.add(group)
        viewer.user_permissions.add(Permission.objects.get(codename="view_device", content_type__app_label="core"))
        self.client.force_login(viewer)

        response = self._search("ZEBRA-OWN-1")
        self.assertContains(response, reverse("assets:device_detail", args=[own.pk]))

        response = self._search("ZEBRA-FOREIGN-1")
        self.assertNotIn("devices", self._group_keys(response))
        self.assertNotContains(response, reverse("assets:device_detail", args=[foreign.pk]))

    # --- no admin links ---------------------------------------------------

    def test_results_never_link_into_the_django_admin(self):
        """Asserted on the fragment, not the full page: the navbar has its own
        (legitimate) admin links, which would mask a bad result link."""
        response = self._search("Zebra", HTTP_HX_REQUEST="true")

        self.assertTrue(response.context["groups"], "expected at least one group for this term")
        self.assertNotContains(response, "/admin/")

    # --- htmx vs full page -------------------------------------------------

    def test_htmx_request_returns_only_the_results_fragment(self):
        """No tiles, no Plotly: those are far too expensive to rebuild per keystroke."""
        response = self._search("ZEBRA-DEVICE-1", HTTP_HX_REQUEST="true")
        body = response.content.decode()

        self.assertNotIn("<html", body)
        self.assertIn('id="global-search-results"', body)
        self.assertIn(reverse("assets:device_detail", args=[self.device.pk]), body)
        self.assertNotIn("tiles", response.context)
        self.assertNotIn("plotly", body.lower())

    def test_a_shared_search_url_reloads_into_the_whole_dashboard(self):
        """?q= is what makes a search bookmarkable: it must render results *and* the dashboard."""
        response = self._search("ZEBRA-DEVICE-1")
        body = response.content.decode()

        self.assertIn("<html", body)
        # The results, rendered server-side rather than waiting for HTMX.
        self.assertIn("devices", self._group_keys(response))
        self.assertIn(reverse("assets:device_detail", args=[self.device.pk]), body)
        # ... and the dashboard's own content, still there below them.
        self.assertTrue(response.context["tiles"])
        self.assertIn("plotly", body.lower())

    def test_the_term_is_reflected_back_into_the_search_input(self):
        """Otherwise a shared link would show results next to an empty box."""
        self.assertContains(self._search("ZEBRA-DEVICE-1"), 'value="ZEBRA-DEVICE-1"')

    # --- "show all" deep links ---------------------------------------------

    def test_show_all_deep_links_carry_the_term_into_the_models_own_list(self):
        group = next(g for g in self._search("ZEBRA-DEVICE-1").context["groups"] if g["source"].key == "devices")
        self.assertEqual(group["show_all_href"], f"{reverse('assets:device_index')}?search=ZEBRA-DEVICE-1")

    def test_the_count_badge_is_itself_the_link_to_the_full_list(self):
        """One control, not a badge plus a separate "show all" link beside it."""
        body = self._search("ZEBRA-DEVICE-1", HTTP_HX_REQUEST="true").content.decode()
        href = f"{reverse('assets:device_index')}?search=ZEBRA-DEVICE-1"

        # The anchor carries the count as its text.
        self.assertRegex(body, rf'<a\s+href="{re.escape(href)}"\s+class="badge[^"]*"[^>]*>\s*1\s*<i')
        # ... and there is no longer a standalone count badge next to it.
        self.assertNotIn('<span class="badge text-bg-secondary">1</span>', body)

    def test_show_all_omits_the_term_where_the_target_cannot_read_it(self):
        """smallstuff's list reads its term from POST, so a ?search= would be a lie."""
        group = next(g for g in self._search("Zebra Headset").context["groups"] if g["source"].key == "smallstuff")
        self.assertEqual(group["show_all_href"], reverse("smallstuff:person_search"))

    # --- the dashboard still works -----------------------------------------

    def test_dashboard_without_a_term_renders_a_bar_and_an_empty_results_panel(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'id="global-search-results"')
        self.assertEqual(response.context["groups"], [])
        # The landing page is still the landing page.
        self.assertTrue(response.context["tiles"])

    def test_the_search_box_is_wired_to_take_the_cursor_on_load(self):
        """`autofocus` for the no-JS case, plus the script that puts the caret at the end."""
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, "autofocus")
        self.assertContains(response, 'id="global-search-input"')
        self.assertContains(response, "setSelectionRange")
        # Restores the typed term after an htmx Back/Forward, which snapshots
        # attributes and so loses it.
        self.assertContains(response, "htmx:historyRestore")

    def test_the_bar_pushes_the_dashboard_url_so_searches_are_shareable(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertContains(response, 'hx-push-url="true"')
        self.assertContains(response, f'hx-get="{reverse("dashboard:index")}"')

    def test_search_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:index"), {"q": "Zebra"})
        self.assertEqual(response.status_code, 302)

    def test_logged_out_htmx_request_refreshes_instead_of_swapping_a_login_page(self):
        """On an expired session a plain 302 would swap the login page into the results panel."""
        self.client.logout()
        response = self._search("Zebra", HTTP_HX_REQUEST="true")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("HX-Refresh"), "true")
        self.assertNotIn(b"csrfmiddlewaretoken", response.content)
