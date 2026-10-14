# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
A refused request names the missing permission, on the 403 page and, over
HTMX, in the flash message (``dlcdb.core.utils.htmx``).
"""

import pytest
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.urls import reverse

from dlcdb.core.utils.htmx import missing_permission_message

pytestmark = pytest.mark.django_db


def _name(app_label, codename):
    return str(Permission.objects.get(content_type__app_label=app_label, codename=codename))


def test_the_403_page_names_the_missing_permission(client, make_user, plain_static):
    client.force_login(make_user())

    response = client.get(reverse("journal:index"))

    assert response.status_code == 403
    assert f"You need the permission: {_name('journal', 'view_journalentry')}" in response.content.decode()


def test_over_htmx_the_flash_message_names_it(client, make_user):
    client.force_login(make_user())

    response = client.get(reverse("journal:index"), headers={"HX-Request": "true"})

    assert response["HX-Refresh"] == "true"
    [message] = get_messages(response.wsgi_request)
    assert _name("journal", "view_journalentry") in str(message)


def test_an_inline_check_names_it(client, make_user, plain_static):
    # The transition's permission is checked before the device is looked up.
    client.force_login(make_user())

    response = client.get(reverse("assets:device_transition", args=[1, "remove"]))

    assert response.status_code == 403
    assert _name("core", "transition_can_remove_device") in response.content.decode()


def test_several_permissions_are_alternatives():
    message = missing_permission_message("core.view_device", "core.change_device")

    assert message == (
        "Permission denied. You need one of these permissions: "
        f"{_name('core', 'view_device')}, {_name('core', 'change_device')}"
    )


def test_the_app_label_tells_permissions_with_the_same_codename_apart():
    # accounts.Group is a proxy of auth.Group: both apps have "change_group".
    assert missing_permission_message("auth.change_group").endswith(_name("auth", "change_group"))
