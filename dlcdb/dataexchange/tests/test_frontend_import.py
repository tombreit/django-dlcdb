# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Integration tests for the frontend device import (upload -> dry-run preview ->
confirm) and the CSV template download.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import translation

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Device
from dlcdb.dataexchange.models import ImporterList
from dlcdb.tenants.models import Tenant

TEST_DATA_DIR = Path("dlcdb/dataexchange/tests/test_data")

IMPORT_URL = "dataexchange:device_import"
CONFIRM_URL = "dataexchange:device_import_confirm"
TEMPLATE_URL = "dataexchange:device_import_template"

pytestmark = pytest.mark.django_db

# The production-like settings use a hashed/manifest static files storage, which
# requires a built manifest (collectstatic). For rendering tests we swap in the
# plain storage so static URL resolution doesn't depend on that build step.
_PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Keep uploaded import files out of the real media directory."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def superuser():
    # The importer resolves the audit `user` FK from the username via a hard
    # lookup, so the importing user needs a non-empty username.
    return CustomUser.objects.create_superuser(email="admin@example.com", password="secret", username="pytestadmin")


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture
def tenant_user(tenant):
    """A non-superuser with the add_device permission, scoped to `tenant`."""
    user = CustomUser.objects.create_user(email="importer@example.com", password="secret", username="pytestimporter")
    user.user_permissions.add(Permission.objects.get(codename="add_device", content_type__app_label="core"))
    group = Group.objects.create(name="pytest-tenant-group")
    user.groups.add(group)
    tenant.groups.add(group)
    return user


def _upload_file(csv_name):
    return SimpleUploadedFile(csv_name, (TEST_DATA_DIR / csv_name).read_bytes(), content_type="text/csv")


@_PLAIN_STATICFILES
def test_import_page_renders_upload_form(superuser_client):
    response = superuser_client.get(reverse(IMPORT_URL))

    assert response.status_code == 200
    assert 'enctype="multipart/form-data"' in response.content.decode()
    assert "EDV_ID" in response.content.decode()  # column list for the user


@_PLAIN_STATICFILES
def test_upload_dry_run_shows_preview_and_writes_nothing(superuser_client, tenant):
    with translation.override("en"):
        response = superuser_client.post(
            reverse(IMPORT_URL),
            {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk},
        )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Confirm import" in content
    assert "CREATED" in content
    # The Detail column says what each row writes.
    assert "new device, in room 355" in content
    assert "new device, lent to ada.lovelace@example.com (room 355)" in content

    # The audit row exists with the archived file, but nothing was written:
    # status is only set by a confirmed (real) import.
    importer_list = ImporterList.objects.get()
    assert importer_list.status == ""
    assert importer_list.tenant == tenant
    assert Device.objects.count() == 0


@_PLAIN_STATICFILES
def test_confirm_writes_devices_and_persists_report(superuser_client, tenant):
    superuser_client.post(reverse(IMPORT_URL), {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk})
    importer_list = ImporterList.objects.get()

    response = superuser_client.post(reverse(CONFIRM_URL, args=[importer_list.pk]))

    assert response.status_code == 302
    assert response.url == reverse("dataexchange:importer_index")

    assert Device.objects.count() > 0
    device = Device.objects.get(edv_id="NTB1282")
    assert device.is_imported is True
    assert device.imported_by == importer_list

    importer_list.refresh_from_db()
    assert importer_list.status == "success"
    assert "created" in importer_list.summary
    assert importer_list.messages


@_PLAIN_STATICFILES
def test_double_confirm_is_rejected(superuser_client, tenant):
    superuser_client.post(reverse(IMPORT_URL), {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk})
    importer_list = ImporterList.objects.get()

    superuser_client.post(reverse(CONFIRM_URL, args=[importer_list.pk]))
    device_count = Device.objects.count()

    with translation.override("en"):
        response = superuser_client.post(reverse(CONFIRM_URL, args=[importer_list.pk]), follow=True)

    assert Device.objects.count() == device_count
    assert "already been processed" in response.content.decode()


@_PLAIN_STATICFILES
def test_missing_columns_show_form_error_and_record_failed_attempt(superuser_client, tenant):
    with translation.override("en"):
        response = superuser_client.post(
            reverse(IMPORT_URL),
            {"file": _upload_file("devices.incompleterowheader.csv"), "tenant": tenant.pk},
        )

    assert response.status_code == 200
    assert "Missing column(s):" in response.content.decode()
    assert Device.objects.count() == 0

    # The failed attempt is part of the import history.
    importer_list = ImporterList.objects.get()
    assert importer_list.status == "error"
    assert "Missing column(s):" in importer_list.messages


@_PLAIN_STATICFILES
def test_wrong_date_format_is_shown_as_a_named_row_error(superuser_client, tenant):
    """The preview names the line, the column and the offending value.

    The user must be able to fix the CSV from this page alone -- previously this
    was a generic field error that said only that *something* was wrong.
    """
    with translation.override("en"):
        response = superuser_client.post(
            reverse(IMPORT_URL),
            {"file": _upload_file("devices.wrongdateformat.csv"), "tenant": tenant.pk},
        )

    assert response.status_code == 200
    content = response.content.decode()

    assert "PURCHASE_DATE" in content
    assert "17.11.2023" in content
    assert "NTB1282" in content

    # Confirming a file with bad rows must not be offered.
    assert response.context["can_confirm"] is False
    assert response.context["report"]["has_errors"] is True
    assert "disabled" in content

    # The failed attempt is part of the import history, with its per-row reason.
    importer_list = ImporterList.objects.get()
    assert importer_list.status == "error"
    assert "PURCHASE_DATE" in importer_list.messages
    assert Device.objects.count() == 0


def test_template_download(superuser_client):
    response = superuser_client.get(reverse(TEMPLATE_URL))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "attachment" in response["Content-Disposition"]
    lines = response.content.decode().splitlines()
    assert lines[0] == ",".join(ImporterList.VALID_COL_HEADERS)
    # Header plus the two example rows (notebook INROOM, smartphone LENT).
    assert len(lines) == 3


@_PLAIN_STATICFILES  # the 403 page renders {% static %} too
def test_views_require_add_device_permission(client):
    user = CustomUser.objects.create_user(email="noperm@example.com", password="secret", username="pytestnoperm")
    client.force_login(user)

    assert client.get(reverse(IMPORT_URL)).status_code == 403
    assert client.post(reverse(CONFIRM_URL, args=[1])).status_code == 403
    assert client.get(reverse(TEMPLATE_URL)).status_code == 403


@_PLAIN_STATICFILES
def test_non_superuser_cannot_spoof_tenant(client, tenant, tenant_user):
    other_tenant = Tenant.objects.create(name="OtherTenant")
    client.force_login(tenant_user)

    response = client.post(
        reverse(IMPORT_URL),
        {"file": _upload_file("devices.correct.csv"), "tenant": other_tenant.pk},
    )

    assert response.status_code == 200
    # The disabled tenant field ignores the submitted value and the view forces
    # the request tenant on the audit row.
    assert ImporterList.objects.get().tenant == tenant


@_PLAIN_STATICFILES
def test_confirm_without_history_permission_redirects_to_device_list(client, tenant, tenant_user):
    """Importing needs only core.add_device; the import history would be a 403."""
    client.force_login(tenant_user)
    client.post(reverse(IMPORT_URL), {"file": _upload_file("devices.correct.csv")})
    importer_list = ImporterList.objects.get()

    response = client.post(reverse(CONFIRM_URL, args=[importer_list.pk]))

    assert response.status_code == 302
    assert response.url == reverse("assets:device_index")
    assert Device.objects.exists()


@_PLAIN_STATICFILES
def test_non_superuser_cannot_confirm_foreign_tenant_row(client, superuser_client, tenant_user):
    other_tenant = Tenant.objects.create(name="OtherTenant")
    superuser_client.post(
        reverse(IMPORT_URL),
        {"file": _upload_file("devices.correct.csv"), "tenant": other_tenant.pk},
    )
    importer_list = ImporterList.objects.get()

    client.force_login(tenant_user)
    response = client.post(reverse(CONFIRM_URL, args=[importer_list.pk]))

    assert response.status_code == 404
    assert Device.objects.count() == 0


@_PLAIN_STATICFILES
def test_preview_lists_every_bad_row_and_blocks_confirm(superuser_client, tenant):
    """The whole point of the dry run: see all the problems in one pass.

    Every failing line is listed with its spreadsheet line number and reason, and
    confirming is refused until they are fixed.
    """
    with translation.override("en"):
        response = superuser_client.post(
            reverse(IMPORT_URL),
            {"file": _upload_file("devices.rowerrors.csv"), "tenant": tenant.pk},
        )

    assert response.status_code == 200
    content = response.content.decode()
    report = response.context["report"]

    assert report["error_count"] == 4
    assert report["has_errors"] is True
    assert response.context["can_confirm"] is False

    # Each failure is actionable from this page alone.
    assert "17.11.2023" in content
    assert "PURCHASE_DATE" in content
    assert "LENDER_EMAIL" in content
    assert "INROOOM" in content

    # And the good rows are still shown as importable.
    assert "ERR-OK-1" in content
    assert "ERR-OK-2" in content
    assert Device.objects.count() == 0


@_PLAIN_STATICFILES
def test_confirming_a_file_with_bad_rows_writes_nothing(superuser_client, tenant):
    """The button is disabled, but a hand-posted confirm must be refused too."""
    with translation.override("en"):
        superuser_client.post(
            reverse(IMPORT_URL),
            {"file": _upload_file("devices.rowerrors.csv"), "tenant": tenant.pk},
        )
        importer_list = ImporterList.objects.get()

        response = superuser_client.post(reverse(CONFIRM_URL, args=[importer_list.pk]), follow=True)

    assert response.status_code == 200
    assert Device.objects.count() == 0
    assert any("nothing was written" in str(message).lower() for message in response.context["messages"])


# --- Django admin importer ----------------------------------------------------
# The admin and the frontend must fail the same way; save_model used to have no
# error handling at all, so any import error there was a traceback page.

ADMIN_ADD_URL = "admin:dataexchange_importerlist_add"


@_PLAIN_STATICFILES
def test_admin_import_with_bad_rows_reports_and_writes_nothing(superuser_client, tenant):
    """The admin surfaces the same failure as the frontend, as a message.

    save_model() had no error handling, so a failure that got past the form's dry
    run (a write-time collision, or an exception type clean() did not catch)
    rendered a traceback page.
    """
    with translation.override("en"):
        response = superuser_client.post(
            reverse(ADMIN_ADD_URL),
            {
                "file": _upload_file("devices.rowerrors.csv"),
                "note": "pytest",
                "import_format": ImporterList.ImportFormatChoices.INTERNALCSV,
                "tenant": tenant.pk,
            },
            follow=True,
        )

    assert response.status_code == 200
    assert Device.objects.count() == 0

    rendered = " ".join(str(message) for message in response.context["messages"])
    assert "nothing was written" in rendered.lower()
