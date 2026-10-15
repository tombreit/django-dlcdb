# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Integration tests for the read-only frontend import history (list + detail)."""

import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse
from django.utils import translation

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import Device
from dlcdb.dataexchange.models import ImporterList
from dlcdb.tenants.models import Tenant

from .test_frontend_import import _PLAIN_STATICFILES, _upload_file

INDEX_URL = "dataexchange:importer_index"
DETAIL_URL = "dataexchange:importer_detail"

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]


@pytest.fixture
def superuser_client(client, join_tenant):
    user = CustomUser.objects.create_superuser(email="admin@example.com", password="secret", username="pytestadmin")
    client.force_login(join_tenant(user))
    return client


@pytest.fixture
def confirmed_import(superuser_client, tenant):
    """A written import, created through the real upload + confirm flow."""
    superuser_client.post(
        reverse("dataexchange:device_import"),
        {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk, "note": "Spring delivery"},
    )
    importer_list = ImporterList.objects.get()
    superuser_client.post(reverse("dataexchange:device_import_confirm", args=[importer_list.pk]))
    importer_list.refresh_from_db()
    return importer_list


def _viewer_client(client, tenant, *, codenames=("view_importerlist",)):
    user = CustomUser.objects.create_user(email="viewer@example.com", password="secret", username="pytestviewer")
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    group = Group.objects.create(name="pytest-viewer-group")
    user.groups.add(group)
    tenant.groups.add(group)
    client.force_login(user)
    return client


@_PLAIN_STATICFILES
def test_index_lists_imports_with_status_and_device_count(superuser_client, confirmed_import):
    unconfirmed = ImporterList.objects.create(file="imported_csv/abandoned.csv", tenant=confirmed_import.tenant)

    with translation.override("en"):
        response = superuser_client.get(reverse(INDEX_URL))

    assert response.status_code == 200
    content = response.content.decode()
    assert confirmed_import.file_name in content
    assert unconfirmed.file_name in content
    assert "Not confirmed" in content
    page_rows = {obj.pk: obj for obj in response.context["page_obj"]}
    assert page_rows[confirmed_import.pk].devices_count == Device.objects.filter(imported_by=confirmed_import).count()
    assert page_rows[confirmed_import.pk].devices_count > 0


@_PLAIN_STATICFILES
def test_an_import_is_named_by_its_file_without_the_upload_folder(superuser_client, tenant):
    named = ImporterList.objects.create(file="imported_csv/spring.csv", tenant=tenant)
    fileless = ImporterList.objects.create(file="", tenant=tenant)

    with translation.override("en"):
        index = superuser_client.get(reverse(INDEX_URL)).content.decode()
        detail = superuser_client.get(reverse(DETAIL_URL, args=[named.pk])).content.decode()
        fileless_detail = superuser_client.get(reverse(DETAIL_URL, args=[fileless.pk])).content.decode()

    assert named.file_name == "spring.csv"
    assert "spring.csv" in index
    assert "imported_csv/spring.csv" not in index
    assert "Import without file" in index
    assert '<h1 class="h3 mb-1">spring.csv</h1>' in detail
    assert '<h1 class="h3 mb-1">Import without file</h1>' in fileless_detail


@_PLAIN_STATICFILES
def test_index_htmx_response_is_fragment_only(superuser_client, confirmed_import):
    response = superuser_client.get(reverse(INDEX_URL), headers={"HX-Request": "true"})

    assert 'id="importer-list"' in response.content.decode()
    assert "<html" not in response.content.decode()


@_PLAIN_STATICFILES
def test_status_filter_and_search(superuser_client, confirmed_import):
    unconfirmed = ImporterList.objects.create(file="imported_csv/abandoned.csv", tenant=confirmed_import.tenant)
    url = reverse(INDEX_URL)

    def listed(params):
        return {obj.pk for obj in superuser_client.get(url, params).context["page_obj"]}

    assert listed({"status": "none"}) == {unconfirmed.pk}
    assert listed({"status": "success"}) == {confirmed_import.pk}
    assert listed({"search": "spring"}) == {confirmed_import.pk}


def test_index_requires_view_permission(client, tenant):
    _viewer_client(client, tenant, codenames=())

    assert client.get(reverse(INDEX_URL)).status_code == 403


@_PLAIN_STATICFILES
def test_tenant_user_sees_only_own_tenant_imports(client, tenant):
    own = ImporterList.objects.create(file="imported_csv/own.csv", tenant=tenant)
    other = ImporterList.objects.create(file="imported_csv/other.csv", tenant=Tenant.objects.create(name="OtherTenant"))
    _viewer_client(client, tenant)

    response = client.get(reverse(INDEX_URL))
    assert [obj.pk for obj in response.context["page_obj"]] == [own.pk]

    assert client.get(reverse(DETAIL_URL, args=[own.pk])).status_code == 200
    assert client.get(reverse(DETAIL_URL, args=[other.pk])).status_code == 404


@_PLAIN_STATICFILES
def test_detail_shows_log_and_is_read_only(superuser_client, confirmed_import):
    url = reverse(DETAIL_URL, args=[confirmed_import.pk])

    response = superuser_client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "NTB1282" in content  # a row of the stored log
    assert f'action="{url}' not in content
    assert f"?imported_by={confirmed_import.pk}" in content
    assert superuser_client.post(url).status_code == 405


@_PLAIN_STATICFILES
def test_device_list_filters_by_import(superuser_client, confirmed_import):
    manual_device = Device.objects.create(edv_id="MANUAL-1", tenant=confirmed_import.tenant)

    response = superuser_client.get(reverse("assets:device_index"), {"imported_by": confirmed_import.pk})

    listed = {device.pk for device in response.context["page_obj"]}
    assert listed == set(Device.objects.filter(imported_by=confirmed_import).values_list("pk", flat=True))
    assert manual_device.pk not in listed


@_PLAIN_STATICFILES
def test_import_pages_and_device_sidebar_link_to_the_frontend(superuser_client, confirmed_import, tenant):
    response = superuser_client.get(reverse("dataexchange:device_import"))
    assert f'href="{reverse(INDEX_URL)}"' in response.content.decode()

    response = superuser_client.post(
        reverse("dataexchange:device_import"), {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk}
    )
    assert response.templates[0].name == "dataexchange/import_preview.html"
    assert f'href="{reverse(INDEX_URL)}"' in response.content.decode()

    device = Device.objects.filter(imported_by=confirmed_import).first()
    response = superuser_client.get(reverse("assets:device_detail", args=[device.pk]))
    assert reverse(DETAIL_URL, args=[confirmed_import.pk]) in response.content.decode()


@_PLAIN_STATICFILES
def test_uploader_is_recorded_and_not_overwritten_on_confirm(client, superuser_client, tenant, join_tenant):
    superuser_client.post(
        reverse("dataexchange:device_import"), {"file": _upload_file("devices.correct.csv"), "tenant": tenant.pk}
    )
    importer_list = ImporterList.objects.get()
    uploader = importer_list.user
    assert uploader.username == "pytestadmin"
    # The denormalized copy is str(user), like every other audit model.
    assert importer_list.username == "admin@example.com"

    other_admin = CustomUser.objects.create_superuser(email="other@example.com", password="secret", username="other")
    client.force_login(join_tenant(other_admin))
    client.post(reverse("dataexchange:device_import_confirm", args=[importer_list.pk]))

    importer_list.refresh_from_db()
    assert importer_list.status == "success"
    assert importer_list.user == uploader

    response = client.get(reverse(DETAIL_URL, args=[importer_list.pk]))
    assert uploader.email in response.content.decode()


@_PLAIN_STATICFILES
def test_admin_import_records_the_uploader(superuser_client, tenant):
    superuser_client.post(
        reverse("admin:dataexchange_importerlist_add"),
        {
            "file": _upload_file("devices.correct.csv"),
            "import_format": ImporterList.ImportFormatChoices.INTERNALCSV,
            "tenant": tenant.pk,
        },
    )

    assert ImporterList.objects.get().username == "admin@example.com"
