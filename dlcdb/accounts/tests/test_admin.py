# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""User admin action "Deactivate selected users"."""

import pytest
from django.contrib.admin.models import CHANGE, LogEntry
from django.urls import reverse

from dlcdb.accounts.models import CustomUser

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

CHANGELIST_URL = reverse("admin:accounts_customuser_changelist")


def _deactivate(client, *users):
    return client.post(
        CHANGELIST_URL,
        {"action": "deactivate", "_selected_action": [user.pk for user in users]},
        follow=True,
    )


@pytest.fixture
def others():
    return [
        CustomUser.objects.create_user(email=f"{name}@example.com", username=name) for name in ("anna", "ben", "carl")
    ]


def test_deactivates_the_selected_users_and_logs_it(client, make_user, others):
    anna, ben, carl = others
    admin = make_user("accounts.view_customuser", "accounts.change_customuser", is_staff=True)
    client.force_login(admin)

    response = _deactivate(client, anna, ben)

    assert "2 users deactivated." in response.text
    active = dict(CustomUser.objects.filter(pk__in=[anna.pk, ben.pk, carl.pk]).values_list("username", "is_active"))
    assert active == {"anna": False, "ben": False, "carl": True}
    entries = LogEntry.objects.filter(user=admin, action_flag=CHANGE, change_message="Deactivated.")
    assert sorted(entry.object_id for entry in entries) == sorted(str(user.pk) for user in (anna, ben))


def test_ones_own_account_stays_active(client, make_user, others):
    anna = others[0]
    admin = make_user("accounts.view_customuser", "accounts.change_customuser", is_staff=True)
    client.force_login(admin)

    response = _deactivate(client, admin, anna)

    assert "You cannot deactivate your own account." in response.text
    assert "1 user deactivated." in response.text
    admin.refresh_from_db()
    assert admin.is_active


def test_needs_the_change_permission(client, make_user, others):
    anna = others[0]
    client.force_login(make_user("accounts.view_customuser", is_staff=True))

    assert 'value="deactivate"' not in client.get(CHANGELIST_URL).text
    _deactivate(client, anna)
    anna.refresh_from_db()
    assert anna.is_active


@pytest.fixture
def full_admin_client(client, make_user):
    client.force_login(
        make_user(
            "accounts.view_customuser",
            "accounts.change_customuser",
            "accounts.delete_customuser",
            is_staff=True,
        )
    )
    return client


def test_deactivate_replaces_the_bulk_delete(full_admin_client):
    content = full_admin_client.get(CHANGELIST_URL).text

    assert 'value="deactivate"' in content
    assert 'value="delete_selected"' not in content


def test_the_change_page_offers_only_the_permanent_delete(full_admin_client, others):
    anna = others[0]

    content = full_admin_client.get(reverse("admin:accounts_customuser_change", args=[anna.pk])).text

    assert reverse("admin:accounts_customuser_delete", args=[anna.pk]) not in content
    assert reverse("admin:accounts_customuser_hard_delete", args=[anna.pk]) in content
    assert "Delete permanently" in content


def test_delete_permanently_removes_the_user(full_admin_client, others):
    anna = others[0]

    full_admin_client.post(reverse("admin:accounts_customuser_hard_delete", args=[anna.pk]))

    assert not CustomUser.objects.filter(pk=anna.pk).exists()
