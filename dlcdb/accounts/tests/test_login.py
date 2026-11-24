# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import importlib
import sys
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

import dlcdb.accounts.auth_backends


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def login_url():
    # /admin/login/ is redirected to the project login view (see dlcdb/urls.py),
    # so authentication happens at reverse("login") == /accounts/login/.
    return reverse("login")


@pytest.fixture
def create_user(db, django_user_model, test_password, settings):
    settings.AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

    def make_user(**kwargs):
        kwargs["password"] = test_password
        if "email" not in kwargs:
            kwargs["email"] = f"{uuid.uuid4()!s}@example.com"
        return django_user_model.objects.create_user(**kwargs)

    return make_user


@pytest.mark.django_db
def test_staff_login_to_admin_with_email(client, create_user, test_password, login_url):
    """Test that a staff user can login with their email address"""
    user = create_user(is_staff=True)

    # Attempt login with email as username (since USERNAME_FIELD = 'email')
    response = client.post(login_url, {"username": user.email, "password": test_password}, follow=False)

    # For a successful login, Django redirects to LOGIN_REDIRECT_URL ("dashboard" == "/")
    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert "_auth_user_id" in client.session

    # Following the redirect should land on a working page
    response = client.post(login_url, {"username": user.email, "password": test_password}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_login_with_username(client, test_password, login_url):
    user = get_user_model().objects.create_user(email="ada@example.com", username="ada", password=test_password)

    response = client.post(login_url, {"username": "ada", "password": test_password})

    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_login_with_email_keeps_the_username(client, test_password, login_url):
    user = get_user_model().objects.create_user(email="ada@example.com", username="ada", password=test_password)

    client.post(login_url, {"username": "ada@example.com", "password": test_password})

    user.refresh_from_db()
    assert client.session["_auth_user_id"] == str(user.pk)
    assert user.username == "ada"


@pytest.mark.django_db
def test_the_email_wins_over_a_username_that_looks_like_it(client, test_password, login_url):
    User = get_user_model()
    # Usernames used to follow the email: this one is Ada's former address.
    User.objects.create_user(email="ada@example.net", username="ada@example.com", password="another-password")
    owner = User.objects.create_user(email="ada@example.com", username="ada", password=test_password)

    client.post(login_url, {"username": "ada@example.com", "password": test_password})

    assert client.session["_auth_user_id"] == str(owner.pk)


@pytest.mark.django_db
def test_wrong_password_shows_the_login_error(client, create_user, login_url):
    user = create_user()

    response = client.post(login_url, {"username": user.email, "password": "not-the-password"})

    assert response.status_code == 200
    assert b"alert-danger" in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_page_offers_a_show_password_button(client, create_user, login_url):
    # create_user swaps in plain static storage, so the page renders.
    create_user()

    content = client.get(login_url).content.decode()

    assert "data-password-toggle" in content
    assert 'aria-controls="id_password"' in content
    assert "accounts/js/password-toggle.js" in content


def test_auth_backends_import_without_django_auth_ldap(monkeypatch):
    """Without the `ldap` extra, the always active EmailModelBackend must still import."""
    monkeypatch.setitem(sys.modules, "django_auth_ldap", None)
    monkeypatch.setitem(sys.modules, "django_auth_ldap.backend", None)
    monkeypatch.delitem(sys.modules, "dlcdb.accounts.auth_backends")
    # The re-import also rebinds the package attribute; restore that as well
    monkeypatch.setattr(dlcdb.accounts, "auth_backends", dlcdb.accounts.auth_backends)

    importlib.import_module("dlcdb.accounts.auth_backends")
