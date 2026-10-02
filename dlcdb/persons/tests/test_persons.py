# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Person frontend."""

import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import localtime

from dlcdb.core import lifecycle
from dlcdb.core.models import Device, InRoomRecord, LentRecord, LostRecord, OrganizationalUnit, Person, Record, Room
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.smallstuff.models import AssignedThing, Thing
from dlcdb.tenants.models import Tenant

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class PersonFrontendTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.unit = OrganizationalUnit.objects.create(name="IT", slug="it")
        cls.local_person = Person.objects.create(
            first_name="Erika",
            last_name="Musterfrau",
            email="erika@example.com",
            organizational_unit=cls.unit,
        )
        cls.synced_person = Person.objects.create(
            first_name="Max",
            last_name="Mustermann",
            email="max@example.com",
            udb_person_uuid="udb-0001",
            udb_person_first_name="Max",
            udb_person_last_name="Mustermann-UDB",
            udb_contract_contract_type="Fellow",
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.index_url = reverse("persons:index")

    def test_index_renders_person_table_with_udb_badge(self):
        response = self.client.get(self.index_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Musterfrau")
        self.assertContains(response, "Mustermann")
        self.assertContains(response, ">HR</span>")
        self.assertContains(response, "Add person")

    def test_index_htmx_response_is_fragment_only(self):
        response = self.client.get(self.index_url, headers={"HX-Request": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="person-list"')
        self.assertNotContains(response, "<html")

    def test_search_matches_udb_mirrored_names_too(self):
        response = self.client.get(self.index_url, {"search": "Mustermann-UDB"}, headers={"HX-Request": "true"})
        self.assertContains(response, "Mustermann")
        self.assertNotContains(response, "Musterfrau")

    def test_organizational_unit_filter(self):
        response = self.client.get(
            self.index_url, {"organizational_unit": self.unit.pk}, headers={"HX-Request": "true"}
        )
        self.assertContains(response, "Musterfrau")
        self.assertNotContains(response, "Mustermann")

    def test_create_person_sets_audit_user(self):
        response = self.client.post(
            reverse("persons:add"),
            {"last_name": "New", "first_name": "Nelly", "email": "nelly@example.com"},
        )

        person = Person.objects.get(email="nelly@example.com")
        self.assertRedirects(response, reverse("persons:detail", args=[person.pk]))
        self.assertEqual(person.user, self.user)

    def test_duplicate_name_is_a_form_error_not_a_crash(self):
        response = self.client.post(
            reverse("persons:add"),
            {"last_name": "musterfrau", "first_name": "erika", "email": "other@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "alert-danger")
        self.assertEqual(Person.objects.filter(email="other@example.com").count(), 0)

    def test_edit_unsynced_person(self):
        url = reverse("persons:detail", args=[self.local_person.pk])
        response = self.client.post(
            url,
            {"last_name": "Musterfrau", "first_name": "Erika", "email": "erika.m@example.com"},
        )

        self.assertRedirects(response, self.index_url)
        self.local_person.refresh_from_db()
        self.assertEqual(self.local_person.email, "erika.m@example.com")

    def test_udb_synced_person_is_readonly_even_for_superusers(self):
        url = reverse("persons:detail", args=[self.synced_person.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<form method="post"')
        self.assertContains(response, "managed by the HR API sync")
        self.assertContains(response, "Mustermann-UDB")

        denied = self.client.post(url, {"last_name": "Hacked", "first_name": "Max", "email": "max@example.com"})
        self.assertEqual(denied.status_code, 403)
        self.synced_person.refresh_from_db()
        self.assertEqual(self.synced_person.last_name, "Mustermann")

    def test_view_only_user_cannot_post(self):
        viewer = get_user_model().objects.create_user(
            username="person-viewer", email="viewer@example.com", password="secret"
        )
        viewer.user_permissions.add(Permission.objects.get(codename="view_person", content_type__app_label="core"))
        self.client.force_login(viewer)

        url = reverse("persons:detail", args=[self.local_person.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"last_name": "X", "first_name": "Y"}).status_code, 403)

    def test_index_requires_view_permission(self):
        nobody = get_user_model().objects.create_user(
            username="person-nobody", email="nobody@example.com", password="secret"
        )
        self.client.force_login(nobody)
        self.assertEqual(self.client.get(self.index_url).status_code, 403)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class PersonAssignmentsTests(TestCase):
    """The lendings, licences and smallstuff cards on the person detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
        cls.tenant = Tenant.objects.create(name="Own tenant")
        # Superusers see only the tenants of their groups.
        group = Group.objects.create(name="Own tenant")
        cls.tenant.groups.add(group)
        cls.user.groups.add(group)
        other_tenant = Tenant.objects.create(name="Other tenant")

        cls.room = Room.objects.create(number="A1.01")
        cls.person = Person.objects.create(first_name="Erika", last_name="Musterfrau", email="erika@example.com")

        cls.current_lending = establish_state(
            LentRecord,
            device=Device.objects.create(edv_id="LENT-NOW", is_lentable=True, tenant=cls.tenant),
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        # Returned: the return date is set and the next record supersedes the lending.
        returned_device = Device.objects.create(edv_id="LENT-PAST", is_lentable=True, tenant=cls.tenant)
        cls.past_lending = establish_state(
            LentRecord,
            device=returned_device,
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2025, 1, 1),
            lent_desired_end_date=datetime.date(2025, 3, 1),
            lent_end_date=datetime.date(2025, 2, 1),
        )
        establish_state(InRoomRecord, device=returned_device, room=cls.room)

        establish_state(
            LentRecord,
            device=Device.objects.create(edv_id="LENT-OTHER-TENANT", is_lentable=True, tenant=other_tenant),
            person=cls.person,
            room=cls.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        cls.licence = Device.objects.create(edv_id="LIC-1", series="Office Suite", is_licence=True, tenant=cls.tenant)
        cls.licence_record = InRoomRecord.objects.create(device=cls.licence, room=cls.room, person=cls.person)

        AssignedThing.objects.create(person=cls.person, thing=Thing.objects.create(name="Door key", slug="door-key"))
        AssignedThing.objects.create(
            person=cls.person,
            thing=Thing.objects.create(name="USB headset", slug="usb-headset"),
            unassigned_at=datetime.datetime(2025, 5, 1, tzinfo=datetime.UTC),
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("persons:detail", args=[self.person.pk])

    def test_current_lending_links_to_lending_record_and_device(self):
        response = self.client.get(self.url)

        self.assertContains(response, "LENT-NOW")
        self.assertContains(response, reverse("lending:detail", args=[self.current_lending.pk]))
        self.assertContains(response, reverse("assets:record_detail", args=[self.current_lending.pk]))
        self.assertContains(response, reverse("assets:device_detail", args=[self.current_lending.device.pk]))

    def test_past_lending_links_to_its_record_only(self):
        response = self.client.get(self.url)

        self.assertContains(response, "2025-01-01 – 2025-02-01")
        self.assertContains(response, reverse("assets:record_detail", args=[self.past_lending.pk]))
        self.assertNotContains(response, reverse("lending:detail", args=[self.past_lending.pk]))

    def test_lending_of_another_tenant_is_hidden(self):
        self.assertNotContains(self.client.get(self.url), "LENT-OTHER-TENANT")

    def test_licence_links_to_licence_and_record(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Office Suite")
        self.assertContains(response, reverse("licenses:edit", args=[self.licence.pk]))
        self.assertContains(response, reverse("assets:record_detail", args=[self.licence_record.pk]))

    def test_lent_licence_is_listed_once_as_lending(self):
        establish_state(
            LentRecord,
            device=Device.objects.create(edv_id="LIC-LENT", is_licence=True, is_lentable=True, tenant=self.tenant),
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2026, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        self.assertContains(self.client.get(self.url), "LIC-LENT", count=1)

    def test_lending_copies_are_one_entry_linking_the_latest_copy(self):
        same_lending = {
            "device": Device.objects.create(edv_id="LENT-COPIED", is_lentable=True, tenant=self.tenant),
            "person": self.person,
            "room": self.room,
            "lent_start_date": datetime.date(2024, 1, 1),
            "lent_desired_end_date": datetime.date(2099, 1, 1),
        }
        original = establish_state(LentRecord, **same_lending)
        # What an inventory stamp used to leave behind: a copy of the active record.
        copy = establish_state(LentRecord, **same_lending)

        response = self.client.get(self.url)
        self.assertContains(response, "LENT-COPIED", count=1)
        self.assertContains(response, reverse("assets:record_detail", args=[copy.pk]))
        self.assertNotContains(response, reverse("assets:record_detail", args=[original.pk]))

    def test_relending_with_another_start_is_its_own_entry(self):
        device = Device.objects.create(edv_id="LENT-TWICE", is_lentable=True, tenant=self.tenant)
        earlier = establish_state(
            LentRecord,
            device=device,
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2023, 1, 1),
            lent_desired_end_date=datetime.date(2023, 3, 1),
            lent_end_date=datetime.date(2023, 2, 1),
        )
        establish_state(InRoomRecord, device=device, room=self.room)
        later = establish_state(
            LentRecord,
            device=device,
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2024, 1, 1),
            lent_desired_end_date=datetime.date(2099, 1, 1),
        )

        response = self.client.get(self.url)
        self.assertContains(response, "LENT-TWICE", count=2)
        self.assertContains(response, reverse("assets:record_detail", args=[earlier.pk]))
        self.assertContains(response, reverse("assets:record_detail", args=[later.pk]))

    def test_lending_ended_without_return_ends_with_its_record(self):
        device = Device.objects.create(edv_id="LENT-LOST", is_lentable=True, tenant=self.tenant)
        lending = establish_state(
            LentRecord,
            device=device,
            person=self.person,
            room=self.room,
            lent_start_date=datetime.date(2025, 6, 1),
            lent_desired_end_date=datetime.date(2025, 7, 1),
        )
        establish_state(LostRecord, device=device)
        lending.refresh_from_db()

        response = self.client.get(self.url)
        self.assertContains(response, f"2025-06-01 – {localtime(lending.effective_until):%Y-%m-%d}")

    def test_licence_copies_are_one_entry_since_the_first_copy(self):
        licence = Device.objects.create(edv_id="LIC-COPIED", series="Design Suite", is_licence=True, tenant=self.tenant)
        first = InRoomRecord.objects.create(device=licence, room=self.room, person=self.person)
        InRoomRecord.objects.create(device=licence, room=self.room, person=self.person)
        Record.objects.filter(pk=first.pk).update(created_at=datetime.datetime(2021, 5, 10, 12, tzinfo=datetime.UTC))

        response = self.client.get(self.url)
        self.assertContains(response, "Design Suite", count=1)
        self.assertContains(response, "Since 2021-05-10")

    def test_a_relocated_licence_stays_one_current_assignment(self):
        licence = Device.objects.create(edv_id="LIC-MOVED", series="CAD Suite", is_licence=True, tenant=self.tenant)
        first = InRoomRecord.objects.create(device=licence, room=self.room, person=self.person)
        Record.objects.filter(pk=first.pk).update(created_at=datetime.datetime(2022, 3, 1, 12, tzinfo=datetime.UTC))

        lifecycle.transition_relocate(licence, room=Room.objects.create(number="B2.02"), user=self.user)

        response = self.client.get(self.url)
        self.assertContains(response, "CAD Suite", count=1)
        self.assertContains(response, "Since 2022-03-01")

    def test_smallstuff_lists_issued_and_returned_items(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Door key")
        self.assertContains(response, "USB headset")
        self.assertContains(response, "2025-05-01")
        self.assertContains(response, reverse("smallstuff:person_detail", args=[self.person.pk]))

    def test_cards_are_listed_for_synced_readonly_person_too(self):
        self.person.udb_person_uuid = "udb-0001"
        self.person.save()

        response = self.client.get(self.url)
        self.assertNotContains(response, '<form method="post"')
        self.assertContains(response, 'id="person-lendings"')

    def test_person_without_assignments_shows_empty_cards(self):
        other = Person.objects.create(last_name="Nobody", email="nobody@example.com")

        response = self.client.get(reverse("persons:detail", args=[other.pk]))
        self.assertContains(response, "No lendings.")
        self.assertContains(response, "No licences.")
        self.assertContains(response, "No smallstuff.")

    def test_cards_need_their_view_permissions(self):
        viewer = get_user_model().objects.create_user(
            username="person-viewer", email="viewer@example.com", password="secret"
        )
        viewer.user_permissions.add(Permission.objects.get(codename="view_person", content_type__app_label="core"))
        self.client.force_login(viewer)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="person-lendings"')
        self.assertNotContains(response, 'id="person-licences"')
        self.assertNotContains(response, 'id="person-smallstuff"')
