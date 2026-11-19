# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Settings › Lending configuration. The shared settings page is tested in licenses/tests/test_configuration.py."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("plain_static")]

URL = reverse("lending:configuration")
VIEW = "lending.view_lendingconfiguration"


@pytest.fixture
def login(client, make_user):
    def _login(*perms):
        client.force_login(make_user(*perms))
        return client

    return _login


@pytest.mark.parametrize(("perms", "status"), [((), 403), ((VIEW,), 200)])
def test_the_page_needs_the_view_permission(login, perms, status):
    assert login(*perms).get(URL).status_code == status


def test_only_the_settings_entry_of_the_menu_is_active(login):
    response = login(VIEW, "core.view_lentrecord").get(URL)

    active = [
        item["url"]
        for item in response.context["nav_items_main"] + response.context["nav_items_settings"]
        if item["active"]
    ]
    assert active == ["lending:configuration"]
