# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Smallstuff gates on the three default AssignedThing permissions: reading who
has what needs ``view_``, handing a thing out needs ``add_``, taking it back
needs ``change_``. The nav entry points at ``person_search`` and requires
``view_assignedthing``, so that view must be reachable with nothing more.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from dlcdb.core.models import Person

from ..models import AssignedThing, Thing


def _make_user(*codenames):
    user = get_user_model().objects.create_user(
        username=f"smallstuff-{'-'.join(codenames) or 'nobody'}",
        email=f"{'-'.join(codenames) or 'nobody'}@example.com",
        password="secret",
    )
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename, content_type__app_label="smallstuff"))
    return user


@pytest.fixture
def person(db):
    return Person.objects.create(first_name="Ada", last_name="Lovelace")


@pytest.fixture
def assignment(db, person):
    return AssignedThing.objects.create(person=person, thing=Thing.objects.create(name="Key", slug="key"))


@pytest.mark.django_db
def test_view_permission_opens_the_index_the_nav_links_to(client, plain_static):
    client.force_login(_make_user("view_assignedthing"))
    assert client.get(reverse("smallstuff:person_search")).status_code == 200


@pytest.mark.django_db
def test_without_any_permission_the_index_is_refused(client, plain_static):
    client.force_login(_make_user())
    assert client.get(reverse("smallstuff:person_search")).status_code == 403


@pytest.mark.django_db
def test_view_permission_opens_the_person_detail(client, plain_static, person):
    client.force_login(_make_user("view_assignedthing"))
    assert client.get(reverse("smallstuff:person_detail", args=[person.pk])).status_code == 200


@pytest.mark.django_db
def test_reading_does_not_allow_assigning(client, plain_static, person):
    client.force_login(_make_user("view_assignedthing"))
    url = reverse("smallstuff:add_assignement", args=[person.pk])
    assert client.get(url).status_code == 403


@pytest.mark.django_db
def test_assigning_needs_the_add_permission(client, plain_static, person):
    client.force_login(_make_user("add_assignedthing"))
    assert client.get(reverse("smallstuff:add_assignement", args=[person.pk])).status_code == 200


@pytest.mark.django_db
def test_returning_a_thing_needs_the_change_permission(client, plain_static, assignment):
    url = reverse("smallstuff:remove_assignement", args=[assignment.pk])

    client.force_login(_make_user("view_assignedthing"))
    assert client.get(url).status_code == 403

    client.force_login(_make_user("change_assignedthing"))
    assert client.get(url).status_code == 204


@pytest.mark.django_db
def test_the_assign_button_is_hidden_from_a_read_only_user(client, plain_static, assignment):
    # Person.smallstuff_person_objects only yields people with an active
    # contract or an outstanding thing, so go through the assigned one.
    url = reverse("smallstuff:person_detail", args=[assignment.person.pk])

    client.force_login(_make_user("view_assignedthing", "add_assignedthing"))
    with_add = client.get(url).content.decode()

    client.force_login(_make_user("view_assignedthing"))
    without_add = client.get(url).content.decode()

    assert "add-thing-button-or-form" in with_add
    assert "add-thing-button-or-form" not in without_add
