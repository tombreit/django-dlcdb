import uuid

import pytest

from django.urls import reverse
from django.contrib import admin
from django.contrib.auth import get_user_model


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def admin_login_url():
    return reverse("admin:login")


@pytest.fixture
def create_user(db, django_user_model, test_password, settings):
    settings.AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

    def make_user(**kwargs):
        kwargs["password"] = test_password
        if "email" not in kwargs:
            kwargs["email"] = f"{str(uuid.uuid4())}@example.com"
        return django_user_model.objects.create_user(**kwargs)

    return make_user


@pytest.mark.django_db
def test_staff_login_to_admin_with_email(client, create_user, test_password, admin_login_url):
    """Test that a staff user can login to the Django admin"""
    user = create_user(is_staff=True)

    # Attempt login with email as username (since USERNAME_FIELD = 'email')
    response = client.post(admin_login_url, {"username": user.email, "password": test_password}, follow=False)

    # For successful login, Django should redirect to the admin index
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:index"))

    # If you want to follow the redirect and check the admin page content
    response = client.post(admin_login_url, {"username": user.email, "password": test_password}, follow=True)
    assert response.status_code == 200
    # Dynamically get the index_title
    assert admin.site.index_title.encode() in response.content


@pytest.mark.django_db
def test_staff_login_to_admin_with_username(client, create_user, test_password, admin_login_url):
    """Test that a staff user with only username cannot login to the Django admin"""
    user = create_user(is_staff=True, username="testuser")

    response = client.post(admin_login_url, {"username": user.username, "password": test_password}, follow=False)

    # Login should fail - check that we're still on the login page with status 200
    assert response.status_code == 200

    # Check we're not redirected to admin index
    assert "admin:index" not in response.url if hasattr(response, "url") else True
    assert b"id_username_error" in response.content
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_legacy_user_login_with_email_and_username_migration(client, test_password, admin_login_url):
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
    response = client.post(admin_login_url, {"username": email, "password": test_password}, follow=False)

    # 3. Verify login succeeds
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:index"))
    assert "_auth_user_id" in client.session

    # 4. Verify username field has been updated to email
    # Refresh user from database
    user.refresh_from_db()

    assert user.username == email  # Username should be updated to email after login

    # Additional verification - can still login with updated username
    client.logout()
    response = client.post(admin_login_url, {"username": user.username, "password": test_password})
    assert response.status_code == 302
