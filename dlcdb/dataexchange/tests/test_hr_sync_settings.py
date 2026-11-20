# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Settings › HR API sync configuration: the token handling, the menu, "Sync now"
and the latest runs. The URL and room rule validation is the model's
(test_udb_sync.py), the shared settings page is tested in
licenses/tests/test_configuration.py.
"""

from unittest import mock

import pytest
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.dataexchange.forms import HrSyncConfigurationForm
from dlcdb.dataexchange.models import UdbSyncConfiguration, UdbSyncRun
from dlcdb.journal.models import JournalEntry

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

URL = reverse("dataexchange:hr_sync")
RUN_URL = reverse("dataexchange:hr_sync_run")
VIEW = "dataexchange.view_udbsyncconfiguration"
CHANGE = "dataexchange.change_udbsyncconfiguration"
TOKEN = "s3cret-token"
HR_URL = "https://hr.example.org/contracts/"


@pytest.fixture
def login(client, make_user):
    def _login(*perms):
        client.force_login(make_user(*perms))
        return client

    return _login


@pytest.fixture
def stored_token():
    config = UdbSyncConfiguration.load()
    config.url = HR_URL
    config.api_token = TOKEN
    config.save()


def _post(client, **fields):
    return client.post(URL, {"url": HR_URL, **fields})


@pytest.mark.parametrize(("perms", "status"), [((), 403), ((VIEW,), 200)])
def test_the_page_needs_the_view_permission(login, perms, status):
    assert login(*perms).get(URL).status_code == status


@pytest.mark.usefixtures("stored_token")
@pytest.mark.parametrize("perms", [(VIEW,), (VIEW, CHANGE)])
def test_the_stored_token_never_reaches_the_browser(login, perms):
    assert TOKEN not in login(*perms).get(URL).content.decode()


@pytest.mark.parametrize("stored", [True, False])
def test_a_stored_token_shows_as_dots(request, login, stored):
    if stored:
        request.getfixturevalue("stored_token")

    content = login(VIEW, CHANGE).get(URL).content.decode()

    assert (f'placeholder="{HrSyncConfigurationForm.TOKEN_MASK}"' in content) == stored


@pytest.mark.usefixtures("stored_token")
def test_an_empty_token_field_keeps_the_token_and_is_no_change(login):
    _post(login(VIEW, CHANGE), enabled="on")  # a change, for the journal entry

    assert UdbSyncConfiguration.load().api_token == TOKEN
    assert "token" not in JournalEntry.objects.get(source="dataexchange.settings").summary


@pytest.mark.usefixtures("stored_token")
def test_a_typed_token_replaces_the_stored_one(login):
    _post(login(VIEW, CHANGE), api_token="new-token")

    assert UdbSyncConfiguration.load().api_token == "new-token"


@pytest.mark.usefixtures("stored_token")
def test_a_changed_url_needs_the_token_again(login):
    client = login(VIEW, CHANGE)
    other_url = "https://elsewhere.example.org/contracts/"

    response = _post(client, url=other_url)
    assert "api_token" in response.context["form"].errors
    assert UdbSyncConfiguration.load().url == HR_URL

    _post(client, url=other_url, api_token=TOKEN)
    assert (UdbSyncConfiguration.load().url, UdbSyncConfiguration.load().api_token) == (other_url, TOKEN)


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


@pytest.fixture
def enabled():
    config = UdbSyncConfiguration.load()
    config.enabled = True
    config.save()


@pytest.fixture
def task():
    with mock.patch("dlcdb.dataexchange.views.task_import_udb_persons") as task:
        yield task


@pytest.mark.usefixtures("enabled")
def test_sync_now_needs_the_change_permission(login, task):
    assert login(VIEW).post(RUN_URL).status_code == 403
    task.assert_not_called()


@pytest.mark.usefixtures("enabled")
def test_sync_now_queues_the_sync(login, task):
    response = login(VIEW, CHANGE).post(RUN_URL)

    assert response.url == URL
    task.assert_called_once_with()


def test_sync_now_queues_nothing_while_the_sync_is_off(login, task):
    login(VIEW, CHANGE).post(RUN_URL)

    task.assert_not_called()


@pytest.mark.parametrize(("perms", "listed"), [((VIEW,), False), ((VIEW, "dataexchange.view_udbsyncrun"), True)])
def test_the_latest_runs_show_their_notes_with_the_run_view_permission(login, perms, listed):
    UdbSyncRun.objects.create(
        status="success", summary="1 unchanged", messages="HR room Gü-999-01 → G999: no such room"
    )

    content = login(*perms).get(URL).content.decode()

    assert ("no such room" in content) == listed


def test_the_admin_action_needs_the_change_permission(make_user):
    request = RequestFactory().get("/")
    request.user = make_user(VIEW, is_staff=True)

    assert "sync_now" not in site.get_model_admin(UdbSyncConfiguration).get_actions(request)
