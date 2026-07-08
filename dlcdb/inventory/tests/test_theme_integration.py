# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Smoke tests for the inventory pages rendered on the shared theme base:
navbar hooks (active-inventory badge, QR toggle), js_vars island, and
the slim per-app asset bundle.
"""

import pytest

from django.urls import reverse

from dlcdb.accounts.models import CustomUser


# Use plain static storage so tests do not require a built staticfiles manifest.
_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@pytest.fixture(autouse=True)
def plain_static_storage(settings):
    settings.STORAGES = _PLAIN_STATIC_STORAGE


@pytest.fixture
def superuser(db):
    return CustomUser.objects.create_superuser(username="smoke_admin", email="smoke_admin@example.org", password="pw")


@pytest.fixture
def su_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture
def device_in_room(db, device_1, room_1):
    # get_inventory_progress() divides by the relevant-device count, so the
    # inventorize pages need at least one device located in a room.
    from dlcdb.core.models import InRoomRecord

    return InRoomRecord.objects.create(device=device_1, room=room_1)


@pytest.mark.django_db
def test_room_list_uses_theme_base(su_client, inventory_1, room_1, device_in_room):
    response = su_client.get(reverse("inventory:inventorize-room-list"))
    assert response.status_code == 200
    html = response.content.decode()

    # Theme shell markers
    assert "theme/dist/css/theme.css" in html
    assert "theme/dist/js/theme.js" in html
    assert "navbar-main" in html  # theme navbar rendered

    # Inventory quirks preserved
    assert 'id="js_vars"' in html and "qrToggleUrl" in html
    assert 'id="qr-toggle"' in html  # QR toggle in user dropdown
    assert "inventory_1" in html  # active inventory badge
    assert 'data-page="inventorize-room-list"' in html
    assert "getCacheBusterParam" in html  # htmx config meta
    assert "inventory/dist/inventory.css" in html
    assert "inventory/dist/inventory.js" in html

    # navigation.py driven items
    assert reverse("inventory:search-devices") in html  # Devices (navbar_secondary)
    assert "/docs/guides/inventur.html" in html  # Docs
    assert reverse("inventory:inventory-lending-report") in html  # VG bei MAs (userdropdown)

    # Old shell must be gone
    assert "dlcdb-inventory-logo" not in html


@pytest.mark.django_db
def test_room_detail_renders(su_client, inventory_1, room_1, device_in_room):
    response = su_client.get(reverse("inventory:inventorize-room", kwargs={"pk": room_1.pk}))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'data-page="inventorize-room-detail"' in html
    assert "is-tom-select" in html  # DeviceAddForm widget class for theme TomSelect init


@pytest.mark.django_db
def test_device_search_has_js_vars_island(su_client, inventory_1):
    # Formerly broken: this view did not pass js_vars; context processor must fix it.
    response = su_client.get(reverse("inventory:search-devices"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "qrToggleUrl" in html
    assert 'id="qr-toggle"' in html


@pytest.mark.django_db
def test_room_qrcodes_renders(su_client, inventory_1, room_1):
    response = su_client.get(reverse("inventory:qr-room-printout", kwargs={"pk": room_1.pk}))
    assert response.status_code == 200


@pytest.mark.django_db
def test_no_active_inventory_alert(su_client, room_1):
    response = su_client.get(reverse("inventory:inventorize-room-list"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "No active inventory" in html  # red navbar badge
    assert "Keine aktive Inventur gefunden" in html  # alert


@pytest.mark.django_db
def test_non_inventory_page_unaffected(su_client, inventory_1):
    response = su_client.get(reverse("dashboard:index"))
    assert response.status_code == 200
    html = response.content.decode()
    assert 'id="qr-toggle"' not in html
    assert "inventory/dist/inventory.js" not in html


@pytest.mark.django_db
def test_qr_toggle_session_endpoint(su_client):
    response = su_client.post(
        reverse("inventory:update-qrtoggle"),
        data='{"qrScanner": 1}',
        content_type="application/json",
    )
    assert response.status_code == 200
    assert su_client.session["qrscanner_enabled"] == 1
