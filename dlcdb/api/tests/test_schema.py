# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The OpenAPI schema and its Swagger UI need a login, or a token for the schema.
DRF views skip the LoginRequiredMiddleware, so they guard themselves.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return get_user_model().objects.create_user(email="api@example.com", password="secret")


def test_anonymous_gets_no_schema(client):
    assert client.get(reverse("schema")).status_code == 403


def test_a_token_gets_the_schema(client, user):
    token = Token.objects.create(user=user)

    response = client.get(reverse("schema"), headers={"Authorization": f"Token {token.key}"})

    assert response.status_code == 200


def test_anonymous_is_sent_from_the_swagger_ui_to_the_login(client):
    url = reverse("swagger-ui")

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


def test_a_logged_in_user_gets_the_swagger_ui_and_the_schema(client, user, plain_static):
    client.force_login(user)

    assert client.get(reverse("swagger-ui")).status_code == 200
    assert client.get(reverse("schema")).status_code == 200
