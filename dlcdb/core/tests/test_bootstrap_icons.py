# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from dlcdb.core.models import DeviceType
from dlcdb.core.utils.bootstrap_icons import get_bootstrap_icons

# Plain static storage so tests do not require a built staticfiles manifest
# (mirrors dlcdb.lending.tests.test_views).
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class BootstrapIconsUtilTests(TestCase):
    def test_returns_installed_icon_set(self):
        icons = get_bootstrap_icons()
        # The compiled theme ships the full bootstrap-icons set.
        self.assertGreater(len(icons), 1000)

        by_name = {icon["name"]: icon["char"] for icon in icons}
        for name in ("laptop", "display", "telephone", "printer"):
            self.assertIn(name, by_name)
            # Each entry maps to a single glyph character.
            self.assertEqual(len(by_name[name]), 1)


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class DeviceTypeIconPickerAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="admin@example.com", password="secret")

    def setUp(self):
        self.client.force_login(self.user)

    def test_add_page_renders_icon_picker(self):
        response = self.client.get(reverse("admin:core_devicetype_add"))
        self.assertEqual(response.status_code, 200)
        # Picker scaffolding from the widget template.
        self.assertContains(response, "data-iconpicker")
        self.assertContains(response, "data-iconpicker-data")
        self.assertContains(response, "Browse")
        # The picker static assets are pulled in via the widget Media.
        self.assertContains(response, "core/admin/iconpicker.js")

    def test_change_page_shows_current_glyph(self):
        char = next(icon["char"] for icon in get_bootstrap_icons() if icon["name"] == "laptop")
        device_type = DeviceType.objects.create(name="Notebook", icon="bi-laptop")
        response = self.client.get(reverse("admin:core_devicetype_change", args=[device_type.pk]))
        self.assertEqual(response.status_code, 200)
        # The preview renders the current icon's glyph.
        self.assertContains(response, char)
