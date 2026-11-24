# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The QR code of a device or room is rendered per request from its URL
(``core.views.qrcode_views``).
"""

import uuid
from io import BytesIO

import pytest
import segno
from django.urls import reverse

pytestmark = pytest.mark.django_db

UUID = uuid.UUID("3f2c1a2b-1234-4abc-9def-0123456789ab")


def _svg(text):
    buffer = BytesIO()
    segno.make_qr(text, error="m").save(buffer, kind="svg")
    return buffer.getvalue()


@pytest.mark.parametrize(("model_name", "text"), [("device", f"DLCDBD{UUID}"), ("room", f"DLCDBR{UUID}")])
def test_the_code_encodes_prefix_infix_and_uuid(client, make_user, model_name, text):
    # Printed labels carry this text: the scanner reads nothing else.
    client.force_login(make_user())

    response = client.get(reverse("core:qrcode", args=[model_name, UUID]))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"
    assert response["Cache-Control"] == "private, max-age=31536000, immutable"
    assert response.content == _svg(text)


def test_an_unknown_model_name_is_a_404(client, make_user):
    client.force_login(make_user())

    assert client.get(f"/core/qrcode/person/{UUID}.svg").status_code == 404


def test_anonymous_is_sent_to_the_login(client):
    response = client.get(reverse("core:qrcode", args=["device", UUID]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))
