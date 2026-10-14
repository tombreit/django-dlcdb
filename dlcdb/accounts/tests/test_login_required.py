# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Every view requires a login (``dlcdb.accounts.middleware.LoginRequiredMiddleware``)
unless it is marked ``login_not_required``.
"""

from django.urls import URLResolver, get_resolver, reverse

# The views anonymous visitors may reach. A new public view belongs here, on
# purpose. DRF views exempt themselves and are guarded by the API's own
# DEFAULT_PERMISSION_CLASSES instead.
PUBLIC_ROUTES = {
    "accounts/login/",
    "accounts/logout/",
    "accounts/password_reset/",
    "accounts/password_reset/done/",
    "accounts/reset/<uidb64>/<token>/",
    "accounts/reset/done/",
    "admin/login/",
    "favicon.ico",
    "i18n/setlang/",
    "media/links/<path:path>",  # regulation files, printed on the lent sheet
}


def _routes(patterns, prefix=""):
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _routes(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            yield prefix + str(pattern.pattern), pattern.callback


def test_only_the_known_views_are_public():
    public = {
        route
        for route, view in _routes(get_resolver().url_patterns)
        if getattr(view, "login_required", True) is False and not hasattr(view, "cls")
    }
    assert public == PUBLIC_ROUTES


def test_anonymous_is_sent_to_the_login(client):
    # The journal view checks only a permission; the login redirect comes
    # from the middleware.
    url = reverse("journal:index")

    response = client.get(url)

    assert response.status_code == 302
    assert response.url == f"{reverse('login')}?next={url}"


def test_anonymous_htmx_request_refreshes_the_page(client):
    # The full page request after the refresh gets the login redirect; the
    # login page is not swapped into the fragment's container.
    response = client.get(reverse("journal:index"), headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert response["HX-Refresh"] == "true"


def test_the_admin_keeps_next_through_its_login_redirect(client):
    # The admin sends anonymous visitors to its own login URL, which forwards
    # to the project's login page.
    response = client.get(reverse("admin:index"))
    assert response.url == f"{reverse('admin:login')}?next=/admin/"

    response = client.get(response.url)
    assert response.url == f"{reverse('login')}?next=/admin/"


def test_logging_out_with_an_expired_session_shows_the_logged_out_page(client, db, plain_static):
    # Not the login page with next=/accounts/logout/, which would end on a 405
    # after logging in: the logout view accepts only POST.
    response = client.post("/accounts/logout/")

    assert response.status_code == 200
    assert "registration/logged_out.html" in [template.name for template in response.templates]


def test_anonymous_can_switch_the_language(client):
    response = client.post(reverse("set_language"), {"language": "de", "next": reverse("login")})

    assert response.status_code == 302
    assert response.url == reverse("login")


def test_anonymous_gets_the_favicon(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    # Reading it to the end lets the test client close the file.
    assert b"".join(response.streaming_content)
