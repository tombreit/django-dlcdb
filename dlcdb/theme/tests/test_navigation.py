# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The ``?next=`` helpers of ``theme.navigation``."""

import pytest
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.theme.navigation import detail_urls, get_redirect_url, with_next

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
