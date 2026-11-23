# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The ``?next=`` helpers of ``theme.navigation``, and the way back from the add pages."""

import re

import pytest
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.theme.navigation import detail_urls, get_redirect_url, get_redirect_url_after_add, with_next

LIST_URL = "/rooms/?search=F2&page=2"


def _get(**params):
    return RequestFactory().get("/somewhere/", params)


def test_get_redirect_url_returns_a_local_path():
    assert get_redirect_url(_get(next=LIST_URL)) == LIST_URL


def test_get_redirect_url_prefers_post_over_get_as_django_does():
    request = RequestFactory().post("/somewhere/?next=/from-get/", {"next": "/from-post/"})

    assert get_redirect_url(request) == "/from-post/"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://evil.example/",
        "//evil.example/",
        # The query string the lists used to send: Django's own check accepts it
        # as a relative URL, which would resolve against the detail page.
        "search=F2&page=2",
    ],
)
def test_get_redirect_url_ignores_anything_but_a_path_on_this_host(value):
    assert get_redirect_url(_get(next=value)) == ""


def test_after_an_add_next_gets_the_new_pk_under_next_field():
    request = _get(next="/assets/devices/7/?next=/assets/devices/&manufacturer=1&supplier=3", next_field="manufacturer")

    # The new pk replaces the earlier one in place; the rest stays.
    assert (
        get_redirect_url_after_add(request, 42) == "/assets/devices/7/?next=/assets/devices/&manufacturer=42&supplier=3"
    )


@pytest.mark.parametrize("next_field", ["", "manu facturer", "a&b", "x=y"])
def test_after_an_add_a_missing_or_odd_next_field_leaves_next_alone(next_field):
    assert get_redirect_url_after_add(_get(next=LIST_URL, next_field=next_field), 42) == LIST_URL


def test_after_an_add_the_field_of_a_prefixed_form_gets_the_new_pk():
    request = _get(next="/assets/devices/7/state/recover/", next_field="p-room")

    assert get_redirect_url_after_add(request, 42) == "/assets/devices/7/state/recover/?p-room=42"


def test_after_an_add_without_a_safe_next_there_is_no_url():
    assert get_redirect_url_after_add(_get(next="https://evil.example/", next_field="room"), 42) == ""


def test_with_next_keeps_slashes_readable_and_encodes_the_query():
    assert with_next("/rooms/1/", LIST_URL) == "/rooms/1/?next=/rooms/%3Fsearch%3DF2%26page%3D2"


def test_with_next_joins_an_existing_query():
    assert with_next("/lending/1/?flow=return", "/lending/") == "/lending/1/?flow=return&next=/lending/"


@pytest.mark.parametrize("value", ["", None])
def test_with_next_leaves_the_url_alone_without_a_target(value):
    assert with_next("/rooms/1/", value) == "/rooms/1/"


def test_detail_urls_return_to_next_and_carry_it_through_the_post():
    next_url, form_action = detail_urls(_get(next=LIST_URL), "rooms:index", "rooms:detail", 1)

    assert next_url == LIST_URL
    assert form_action == with_next(reverse("rooms:detail", args=[1]), LIST_URL)


def test_detail_urls_drop_an_unsafe_next():
    next_url, form_action = detail_urls(_get(next="https://evil.example/"), "rooms:index", "rooms:detail", 1)

    assert next_url == reverse("rooms:index")
    assert form_action == reverse("rooms:detail", args=[1])


# Every add page: the header's back link and the action bar's Cancel, once each
# and to the same place; the device and tenant add pages had a Cancel without URL.
ADD_PAGES = [
    "assets:device_add",
    "assets:device_type:add",
    "assets:manufacturer:add",
    "assets:supplier:add",
    "lending:profile:add",
    "lending:regulation:add",
    "organization:position:add",
    "organization:unit:add",
    "persons:add",
    "rooms:add",
    "smallstuff:thing:add",
    "tenants:add",
]


@pytest.mark.parametrize("route", ADD_PAGES)
def test_an_add_page_has_one_cancel_and_a_back_link_to_the_same_place(db, client, route):
    client.force_login(CustomUser.objects.create_superuser(email="admin@example.com", password="secret"))

    html = client.get(reverse(route)).content.decode()

    cancels = re.findall(r'<a [^>]*href="([^"]*)"[^>]*>\s*Cancel\s*</a>', html)
    backs = re.findall(
        r'<a href="([^"]*)" class="btn btn-outline-secondary[^"]*">\s*<i class="bi bi-arrow-left">', html
    )
    assert len(cancels) == 1 and cancels[0], cancels
    assert backs == cancels
