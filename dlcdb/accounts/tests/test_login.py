# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import importlib
import sys
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


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
    # The login template references collected static assets (theme.css) via the
    # manifest storage; use the plain storage so it renders without collectstatic.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }

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
def test_staff_login_to_admin_with_username(client, create_user, test_password, login_url):
    """Test that a staff user cannot login with their (legacy) username instead of email"""
    user = create_user(is_staff=True, username="testuser")

    response = client.post(login_url, {"username": user.username, "password": test_password}, follow=False)

    # Login should fail - we stay on the login page (status 200). The login form
    # takes an email address, so a username is rejected at the field.
    assert response.status_code == 200
    assert "username" in response.context["form"].errors
    assert "_auth_user_id" not in client.session


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


@pytest.mark.django_db
def test_legacy_user_login_with_email_and_username_migration(client, test_password, login_url):
    """
    Test that a legacy user with username can login with email and username is migrated.
    This basically also tests our custom accounts.auth_backends.EmailModelBackend.
    """

    # 1. Create a "legacy" user with different username and email
    User = get_user_model()
    username = "legacy_username"
    email = "legacy_user@example.com"

    # Create user the traditional way with separate username/email
    user = User.objects.create_user(username=username, email=email, password=test_password, is_staff=True)
    print(f"{user.username=}, {user.email=}")

    # 2. Attempt login with email
    response = client.post(login_url, {"username": email, "password": test_password}, follow=False)

    # 3. Verify login succeeds
    assert response.status_code == 302
    assert response.url == reverse("dashboard")
    assert "_auth_user_id" in client.session

    # 4. Verify username field has been updated to email
    # Refresh user from database
    user.refresh_from_db()

    assert user.username == email  # Username should be updated to email after login

    # Additional verification - can still login with updated username
    client.logout()
    response = client.post(login_url, {"username": user.username, "password": test_password})
    assert response.status_code == 302


def test_auth_backends_import_without_django_auth_ldap(monkeypatch):
    """Without the `ldap` extra, the always active EmailModelBackend must still import."""
    monkeypatch.setitem(sys.modules, "django_auth_ldap", None)
    monkeypatch.setitem(sys.modules, "django_auth_ldap.backend", None)
    monkeypatch.delitem(sys.modules, "dlcdb.accounts.auth_backends", raising=False)

    importlib.import_module("dlcdb.accounts.auth_backends")
