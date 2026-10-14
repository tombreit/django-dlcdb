# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Django serves MEDIA_ROOT behind the login (``core.views.media_views``); only
the regulation files under links/ are public.
"""

import pytest
from django.apps import apps
from django.conf import settings
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
    client.force_login(make_user())
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
    ],
)
def test_anything_else_is_not_found(logged_in, files, path):
    assert logged_in.get(path).status_code == 404


def test_the_public_directory_cannot_be_left(client, files):
    assert client.get("/media/links/../qrcode/DLCDB-1.svg").status_code == 404


def test_every_upload_directory_is_known():
    upload_directories = {
        field.generate_filename(None, "file.txt").split("/")[0]
        for model in apps.get_models()
        for field in model._meta.get_fields()
        if isinstance(field, models.FileField)
    }
    # inventory/sap.py writes its comparison results directly.
    upload_directories.add(settings.SAP_LIST_COMPARISON_RESULT_FOLDER)

    assert upload_directories == media_views.MEDIA_DIRECTORIES
