# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the standalone Person frontend."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import OrganizationalUnit, Person


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
