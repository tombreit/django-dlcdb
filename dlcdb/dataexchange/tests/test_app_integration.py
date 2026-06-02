# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Regression guards for the core -> dataexchange app move.

These encode the invariants verified manually against the production database:
the moved models keep the expected (renamed) table names, the cross-app
``Device.imported_by`` foreign key resolves in both directions, and the admin
routes for the moved models are registered under the new ``dataexchange``
app label.
"""

import pytest
from django.contrib.admin.sites import site
from django.test import override_settings
from django.urls import reverse

from dlcdb.dataexchange.models import ImporterList, RemoverList
from dlcdb.core.models import Device


# The production-like settings use a hashed/manifest static files storage, which
# requires a built manifest (collectstatic). For rendering tests we swap in the
# plain storage so static URL resolution doesn't depend on that build step.
_PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)


def test_models_use_renamed_tables():
    # The data-preserving migration renamed core_* -> dataexchange_*.
    assert ImporterList._meta.db_table == "dataexchange_importerlist"
    assert RemoverList._meta.db_table == "dataexchange_removerlist"


def test_imported_by_points_to_dataexchange():
    field = Device._meta.get_field("imported_by")
    assert field.related_model is ImporterList
    assert field.related_model._meta.app_label == "dataexchange"


@pytest.mark.django_db
def test_device_imported_by_cross_app_fk_roundtrips():
    importer = ImporterList.objects.create(file="imported_csv/regression.csv")
    device = Device.objects.create(edv_id="FK-ROUNDTRIP-1", is_imported=True, imported_by=importer)

    device.refresh_from_db()
    assert isinstance(device.imported_by, ImporterList)
    assert device.imported_by_id == importer.pk

    # Reverse accessor (dataexchange -> core) works too.
    assert importer.device_set.filter(pk=device.pk).exists()


def test_admin_routes_registered_under_new_label():
    assert reverse("admin:dataexchange_importerlist_changelist") == "/admin/dataexchange/importerlist/"
    assert reverse("admin:dataexchange_removerlist_changelist") == "/admin/dataexchange/removerlist/"
    # Detail (change) views must resolve too — the Device admin links to them.
    assert reverse("admin:dataexchange_importerlist_change", args=(1,)) == "/admin/dataexchange/importerlist/1/change/"
    assert reverse("admin:dataexchange_removerlist_change", args=(1,)) == "/admin/dataexchange/removerlist/1/change/"


@pytest.mark.django_db
def test_device_admin_imported_by_link_resolves():
    """
    The Device admin renders a link to the importer's change view. After the
    move this must target the dataexchange app label (regression: it previously
    pointed at the removed ``admin:core_importerlist_change`` and raised
    NoReverseMatch on the device change page).
    """
    importer = ImporterList.objects.create(file="imported_csv/link.csv")
    device = Device.objects.create(edv_id="LINK-1", is_imported=True, imported_by=importer)

    device_admin = site._registry[Device]
    html = device_admin.get_imported_by_link(device)

    assert f"/admin/dataexchange/importerlist/{importer.pk}/change/" in html


@pytest.mark.django_db
@_PLAIN_STATICFILES
def test_device_change_page_renders_with_imported_by(admin_client, test_site):
    """
    End-to-end smoke test: render the actual Device admin change page for an
    imported device. This catches admin-link regressions (such as a stale
    ``admin:core_importerlist_change`` reverse) that only surface when the page
    is rendered for a device whose ``imported_by`` is set.
    """
    importer = ImporterList.objects.create(file="imported_csv/page.csv")
    device = Device.objects.create(edv_id="PAGE-1", is_imported=True, imported_by=importer)

    url = reverse("admin:core_device_change", args=(device.pk,))
    response = admin_client.get(url)

    assert response.status_code == 200
    assert f"/admin/dataexchange/importerlist/{importer.pk}/change/" in response.content.decode()
