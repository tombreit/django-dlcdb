# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Settings › Licenses configuration, and with it the shared settings page (theme/settings_page.py)."""

import pytest
from django.urls import reverse

from dlcdb.core.models import Person
from dlcdb.journal.models import JournalEntry
from dlcdb.licenses.models import LicensesConfiguration

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

URL = reverse("licenses:configuration")
VIEW = "licenses.view_licensesconfiguration"
CHANGE = "licenses.change_licensesconfiguration"


@pytest.fixture
def login(client, make_user):
    """Log in a non-staff user with the given permissions: the page needs no admin access."""

    def _login(*perms):
        client.force_login(make_user(*perms))
        return client

    return _login


@pytest.fixture
def person():
    return Person.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.com")


@pytest.mark.parametrize(("perms", "status"), [((), 403), ((VIEW,), 200)])
def test_the_page_needs_the_view_permission(login, perms, status):
    assert login(*perms).get(URL).status_code == status


def test_without_the_change_permission_the_form_is_read_only(login, person):
    LicensesConfiguration.load().default_subscribers.add(person)

    response = login(VIEW).get(URL)

    assert response.context["form"].fields["default_subscribers"].disabled
    content = response.content.decode()
    assert "Lovelace" in content
    assert "Save changes" not in content


def test_saving_needs_the_change_permission(login, person):
    response = login(VIEW).post(URL, {"default_subscribers": [person.pk]})

    assert response.status_code == 403
    assert not LicensesConfiguration.load().default_subscribers.exists()


def test_a_save_returns_to_the_page_and_is_journaled(login, person):
    response = login(VIEW, CHANGE).post(URL, {"default_subscribers": [person.pk]}, follow=True)

    assert response.redirect_chain == [(URL, 302)]
    assert "Licenses configuration saved." in [str(message) for message in response.context["messages"]]
    assert list(LicensesConfiguration.load().default_subscribers.all()) == [person]
    entry = JournalEntry.objects.get(source="licenses.settings")
    assert entry.summary == "Licenses configuration changed: Default subscribers"


def test_a_save_without_changes_is_not_journaled(login):
    login(VIEW, CHANGE).post(URL, {})

    assert not JournalEntry.objects.filter(source="licenses.settings").exists()


def test_a_save_returns_to_next(login):
    next_url = reverse("licenses:index")

    response = login(VIEW, CHANGE).post(f"{URL}?next={next_url}", {})

    assert response.url == next_url


def test_only_the_settings_entry_of_the_menu_is_active(login):
    response = login(VIEW, "core.view_licencerecord").get(URL)

    active = [
        item["url"]
        for item in response.context["nav_items_main"] + response.context["nav_items_settings"]
        if item["active"]
    ]
    assert active == ["licenses:configuration"]
