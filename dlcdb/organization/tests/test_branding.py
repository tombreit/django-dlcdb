# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Settings › Branding. The shared settings page is tested in licenses/tests/test_configuration.py."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from dlcdb.organization.models import Branding

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("media_root")]

URL = reverse("organization:branding")
VIEW = "organization.view_branding"
CHANGE = "organization.change_branding"


@pytest.fixture
def editor(client, make_user):
    client.force_login(make_user(VIEW, CHANGE))
    return client


def _post_data(**fields):
    """The required fields as stored, plus the given ones."""
    branding = Branding.load()
    return {
        "organization_name_en": branding.organization_name_en,
        "organization_name_de": branding.organization_name_de,
        "organization_abbr": branding.organization_abbr,
        **fields,
    }


@pytest.mark.parametrize(("perms", "status"), [((), 403), ((VIEW,), 200)])
def test_the_page_needs_the_view_permission(client, make_user, perms, status):
    client.force_login(make_user(*perms))
    assert client.get(URL).status_code == status


def test_the_page_uploads_files(editor):
    assert 'enctype="multipart/form-data"' in editor.get(URL).content.decode()


def test_an_svg_logo_is_saved(editor):
    logo = SimpleUploadedFile("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", content_type="image/svg+xml")

    response = editor.post(URL, _post_data(organization_logo_black=logo))

    assert response.status_code == 302
    assert Branding.load().organization_logo_black.name.startswith("branding/logo")


def test_a_logo_that_is_no_svg_is_refused(editor):
    logo = SimpleUploadedFile("logo.png", b"\x89PNG", content_type="image/png")

    response = editor.post(URL, _post_data(organization_logo_black=logo))

    assert response.status_code == 200
    assert response.context["form"].errors["organization_logo_black"]
    assert not Branding.load().organization_logo_black
