# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Integration tests for the shared theme partials and page frames.

These cover the fragments and base templates that several apps now render
through one file, so a change in `theme/` cannot silently break a consumer. The
picker partials in particular have no other coverage: they are swapped in by
HTMX and never touched by the page-level tests.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import override_settings
from django.urls import reverse

from dlcdb.core.models import InRoomRecord, Inventory, Person, Room
from dlcdb.core.tests.basetest import BaseTest

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class SharedPersonPickerTests(BaseTest):
    """theme/includes/_person_search_results.html + _person_list_item.html."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="picker@example.com", password="secret")
        Person.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.com")

    def setUp(self):
        self.client.force_login(self.user)

    def test_both_search_endpoints_render_the_same_shared_card(self):
        # The two views reach the shared template through different backends
        # (a plain queryset vs. a django-filter FilterSet), so both must end up
        # supplying the same (people, query) contract.
        for name, url, field in [
            ("assets", reverse("assets:person_search"), "q_person"),
            ("lending", reverse("lending:person_search"), "search"),
        ]:
            with self.subTest(view=name):
                hit = self.client.post(url, {field: "Lovelace"})
                self.assertEqual(hit.status_code, 200)
                self.assertContains(hit, "js-picker-option")
                self.assertContains(hit, "Lovelace, Ada")
                # picker.js needs these to wire the card into the form.
                self.assertContains(hit, "data-option-id")
                self.assertContains(hit, "data-contract-end")

                miss = self.client.post(url, {field: "zzzznomatch"})
                self.assertContains(miss, "No matching person found.")

                blank = self.client.post(url, {})
                self.assertNotContains(blank, "js-picker-option")
                self.assertNotContains(blank, "No matching person found.")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class SharedFormChromeTests(BaseTest):
    """_form_action_bar.html, _readonly_notice.html and _back_link.html."""

    @classmethod
    def setUpTestData(cls):
        cls.editor = get_user_model().objects.create_superuser(email="editor@example.com", password="secret")
        cls.viewer = get_user_model().objects.create_user(
            username="room-viewer", email="viewer@example.com", password="secret"
        )
        cls.viewer.is_staff = True
        cls.viewer.save()
        cls.viewer.user_permissions.add(
            Permission.objects.get(codename="view_room", content_type__app_label="core")
        )
        cls.room = Room.objects.create(number="A1.01")

    def test_action_bar_default_and_custom_submit_label(self):
        self.client.force_login(self.editor)

        detail = self.client.get(reverse("rooms:detail", args=[self.room.pk]))
        self.assertContains(detail, "Save changes")
        self.assertContains(detail, "bi-check-lg")

        # The add form passes its own submit_label through the same partial.
        add = self.client.get(reverse("rooms:add"))
        self.assertContains(add, "bi-check-lg")

    def test_readonly_notice_and_back_link_without_change_permission(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("rooms:detail", args=[self.room.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "do not have permission to edit it")
        self.assertContains(response, "bi-eye")
        self.assertContains(response, "Back to list")
        self.assertContains(response, "bi-arrow-left")
        # Read-only means no form chrome at all.
        self.assertNotContains(response, "Save changes")


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class InventoryThemePagerTests(BaseTest):
    """The inventory device search now uses theme/includes/_pagination.html."""

    PER_PAGE = 25
    TOTAL = 30

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="pager@example.com", password="secret")
        room = Room.objects.create(number="B1.01")
        Inventory.objects.create(name="Inv", is_active=True)
        for i in range(cls.TOTAL):
            device = cls()._create_device(edv_id=f"EDV-{i:03}", sap_id=f"sap-{i}")
            InRoomRecord.objects.create(device=device, room=room)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("inventory:search-devices")

    def _get(self, **params):
        return self.client.get(self.url, params, HTTP_HX_REQUEST="true").content.decode()

    def test_pages_and_preserves_active_filter(self):
        first = self._get()
        self.assertIn('class="pagination', first)
        self.assertEqual(first.count("inventory_row"), self.PER_PAGE)
        self.assertIn("?page=2", first)

        second = self._get(page=2)
        self.assertEqual(second.count("inventory_row"), self.TOTAL - self.PER_PAGE)

        # {% querystring %} must carry the active filter into every page link,
        # which is what the hand-rolled ?page=N&{{ parameters }} links used to do.
        filtered = self._get(q="EDV-0")
        self.assertIn("q=EDV-0", filtered)

    def test_show_all_override(self):
        content = self._get(show_all="1")
        self.assertEqual(content.count("inventory_row"), self.TOTAL)
        self.assertIn("Show paginated view", content)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE, LANGUAGE_CODE="en")
class IndexFrameTests(BaseTest):
    """theme/_index_base.html + theme/includes/_list_status.html."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="frame@example.com", password="secret")
        Room.objects.create(number="A1.01")

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_status_does_not_relabel_the_clear_all_link(self):
        # _list_status.html includes chips.html without `only`, and
        # theme/filterbar/_clear_all.html takes an optional `label` of its own.
        # Passing the count sentence as `label` would leak down and rename
        # "Clear all" to "1 of 1 room".
        response = self.client.get(reverse("rooms:index"), {"search": "A1"}, headers={"HX-Request": "true"})
        content = response.content.decode()

        self.assertIn("Clear all", content)
        self.assertIn("of 1 room", content)

    def test_heading_stays_outside_the_licenses_swap_target(self):
        # The "Add license" button swaps its form into #licenses-content-wrapper.
        # If the shared frame wrapped the heading in that div too, opening the
        # form would wipe out the h1 and the button itself.
        content = self.client.get(reverse("licenses:index")).content.decode()

        self.assertLess(
            content.index("Add license"),
            content.index('id="licenses-content-wrapper"'),
            "the add button must render before (outside) its own swap target",
        )
