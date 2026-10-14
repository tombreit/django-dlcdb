# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The 403 and login pages show a contact address: the Branding IT address, else
``DEFAULT_FROM_EMAIL``, which reaches them through the ``django_settings``
context processor.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from dlcdb.organization.models import Branding


@pytest.fixture
def no_it_dept_email(db):
    branding = Branding.load()
    branding.organization_it_dept_email = ""
    branding.save()


def test_login_page_shows_the_default_from_email(client, settings, plain_static, no_it_dept_email):
    settings.DEFAULT_FROM_EMAIL = "fallback@example.org"

    response = client.get("/accounts/login/")

    assert 'href="mailto:fallback@example.org"' in response.content.decode()


def test_403_page_shows_the_default_from_email(client, settings, plain_static, no_it_dept_email):
    settings.DEFAULT_FROM_EMAIL = "fallback@example.org"
    client.force_login(get_user_model().objects.create_user(email="nobody@example.com", password="secret"))

    response = client.get(reverse("journal:index"))

    assert response.status_code == 403
    assert 'href="mailto:fallback@example.org"' in response.content.decode()


def test_403_page_shows_the_it_dept_email(client, plain_static, db):
    branding = Branding.load()
    branding.organization_it_dept_email = "it@example.org"
    branding.save()
    client.force_login(get_user_model().objects.create_user(email="nobody@example.com", password="secret"))

    response = client.get(reverse("journal:index"))

    assert response.status_code == 403
    assert 'href="mailto:it@example.org"' in response.content.decode()
