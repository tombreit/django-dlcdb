# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Django serves MEDIA_ROOT behind the login (``core.views.media_views``); only
the regulation files under links/ are public. Each directory requires the
permission of the screens that link its files.
"""

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import models
from django.urls import reverse

from dlcdb.core.views import media_views

pytestmark = pytest.mark.django_db

SVG = '<svg xmlns="http://www.w3.org/2000/svg"><rect width="1" height="1"/></svg>'


@pytest.fixture
def files(media_root):
    for name, content in [
        ("qrcode/DLCDB-1.svg", SVG),
        ("links/policy.pdf", "%PDF-1.4"),
        ("secret/notes.txt", "not served"),
    ]:
        (media_root / name).parent.mkdir(exist_ok=True)
        (media_root / name).write_text(content)


@pytest.fixture
def logged_in(client, make_user):
    client.force_login(make_user("core.view_device"))
    return client


def _content(response):
    # Reading a FileResponse to the end lets the test client close the file.
    return b"".join(response.streaming_content)


def test_anonymous_is_sent_to_the_login(client, files):
    response = client.get("/media/qrcode/DLCDB-1.svg")

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next=/media/qrcode/DLCDB-1.svg"


def test_anonymous_gets_a_regulation(client, files):
    response = client.get("/media/links/policy.pdf")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert "Content-Security-Policy" not in response
    assert _content(response) == b"%PDF-1.4"


def test_a_logged_in_user_gets_the_file(logged_in, files):
    response = logged_in.get("/media/qrcode/DLCDB-1.svg")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert response["Cache-Control"] == "private, no-cache"
    assert response["Content-Security-Policy"] == media_views.ACTIVE_CONTENT_POLICY
    # An opaque origin without forms: an uploaded page cannot phish in the app's name.
    assert "sandbox" in response["Content-Security-Policy"]
    assert _content(response) == SVG.encode()


def test_an_unchanged_file_answers_304(logged_in, files):
    first = logged_in.get("/media/qrcode/DLCDB-1.svg")
    _content(first)
    last_modified = first["Last-Modified"]

    response = logged_in.get("/media/qrcode/DLCDB-1.svg", headers={"If-Modified-Since": last_modified})

    assert response.status_code == 304


@pytest.mark.parametrize(
    "path",
    [
        "/media/secret/notes.txt",  # not an upload directory
        "/media/qrcode/missing.svg",
        "/media/qrcode",
        "/media/qrcode/",
        "/media/qrcode/../secret/notes.txt",
        "/media/qrcode/../../manage.py",
        "/media/qrcode/a%00b.svg",  # the file system calls would raise ValueError
    ],
)
def test_anything_else_is_not_found(logged_in, files, path):
    assert logged_in.get(path).status_code == 404


def test_the_public_directory_cannot_be_left(client, files):
    assert client.get("/media/links/../qrcode/DLCDB-1.svg").status_code == 404


def test_a_nul_byte_in_a_public_path_is_not_found(client, files):
    assert client.get("/media/links/a%00b.pdf").status_code == 404


def test_every_upload_directory_is_known():
    upload_directories = {
        field.generate_filename(None, "file.txt").split("/")[0]
        for model in apps.get_models()
        for field in model._meta.get_fields()
        if isinstance(field, models.FileField)
    }
    # inventory/sap.py writes its comparison results directly.
    upload_directories.add(settings.SAP_LIST_COMPARISON_RESULT_FOLDER)

    assert upload_directories == set(media_views.MEDIA_PERMISSIONS)


def test_every_permission_exists():
    # A typo would refuse everyone but superusers.
    for permissions in media_views.MEDIA_PERMISSIONS.values():
        for permission in permissions:
            app_label, codename = permission.split(".")
            assert Permission.objects.filter(content_type__app_label=app_label, codename=codename).exists(), permission


GUARDED = [(directory, permissions) for directory, permissions in media_views.MEDIA_PERMISSIONS.items() if permissions]


@pytest.mark.parametrize(("directory", "permissions"), GUARDED, ids=[directory for directory, _ in GUARDED])
def test_each_guarded_directory_needs_one_of_its_permissions(client, make_user, media_root, directory, permissions):
    (media_root / directory).mkdir()
    (media_root / directory / "file.txt").write_text("content")
    url = f"/media/{directory}/file.txt"

    client.force_login(make_user(email="nobody@example.com"))
    assert client.get(url).status_code == 403

    for number, permission in enumerate(permissions):
        client.force_login(make_user(permission, email=f"user{number}@example.com"))
        response = client.get(url)
        assert response.status_code == 200, permission
        assert _content(response) == b"content"


def test_the_refusal_names_the_permissions(client, make_user, files, plain_static):
    client.force_login(make_user())

    response = client.get("/media/qrcode/DLCDB-1.svg")

    assert response.status_code == 403
    assert "You need one of these permissions:" in response.content.decode()


def test_a_refused_user_gets_no_304(client, make_user, files):
    client.force_login(make_user())

    response = client.get("/media/qrcode/DLCDB-1.svg", headers={"If-Modified-Since": "Fri, 01 Jan 2100 00:00:00 GMT"})

    assert response.status_code == 403


def test_branding_is_open_to_every_logged_in_user(client, make_user, media_root):
    (media_root / "branding").mkdir()
    (media_root / "branding" / "logo.svg").write_text(SVG)
    client.force_login(make_user())

    response = client.get("/media/branding/logo.svg")

    assert response.status_code == 200
    assert _content(response) == SVG.encode()
