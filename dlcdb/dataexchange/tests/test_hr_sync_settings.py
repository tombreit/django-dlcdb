# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Settings › HR API sync configuration: the token handling and the menu. The URL
and room rule validation is the model's (test_udb_sync.py), the shared settings
page is tested in licenses/tests/test_configuration.py.
"""

import pytest
from django.urls import reverse

from dlcdb.dataexchange.models import UdbSyncConfiguration
from dlcdb.journal.models import JournalEntry

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

URL = reverse("dataexchange:hr_sync")
VIEW = "dataexchange.view_udbsyncconfiguration"
CHANGE = "dataexchange.change_udbsyncconfiguration"
TOKEN = "s3cret-token"


@pytest.fixture
def login(client, make_user):
    def _login(*perms):
        client.force_login(make_user(*perms))
        return client

    return _login


@pytest.fixture
def stored_token():
    config = UdbSyncConfiguration.load()
    config.api_token = TOKEN
    config.save()


def _post(client, **fields):
    return client.post(URL, {"url": "https://hr.example.org/contracts/", **fields})


@pytest.mark.parametrize(("perms", "status"), [((), 403), ((VIEW,), 200)])
def test_the_page_needs_the_view_permission(login, perms, status):
    assert login(*perms).get(URL).status_code == status


@pytest.mark.usefixtures("stored_token")
@pytest.mark.parametrize("perms", [(VIEW,), (VIEW, CHANGE)])
def test_the_stored_token_never_reaches_the_browser(login, perms):
    assert TOKEN not in login(*perms).get(URL).content.decode()


@pytest.mark.usefixtures("stored_token")
def test_an_empty_token_field_keeps_the_token_and_is_no_change(login):
    _post(login(VIEW, CHANGE))

    assert UdbSyncConfiguration.load().api_token == TOKEN
    assert "token" not in JournalEntry.objects.get(source="dataexchange.settings").summary


@pytest.mark.usefixtures("stored_token")
def test_a_typed_token_replaces_the_stored_one(login):
    _post(login(VIEW, CHANGE), api_token="new-token")

    assert UdbSyncConfiguration.load().api_token == "new-token"


@pytest.mark.usefixtures("stored_token")
def test_remove_token_clears_it(login):
    _post(login(VIEW, CHANGE), remove_api_token="on")

    assert UdbSyncConfiguration.load().api_token == ""


def test_only_the_settings_entry_of_the_menu_is_active(login):
    response = login(VIEW, "dataexchange.view_importerlist").get(URL)

    active = [
        item["url"]
        for item in response.context["nav_items_processes"] + response.context["nav_items_settings"]
        if item["active"]
    ]
    assert active == ["dataexchange:hr_sync"]
