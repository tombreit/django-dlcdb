# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The units and positions persons hold (views.UnitViewSet, views.PositionViewSet)."""

import pytest
from django.urls import reverse

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit, Person

pytestmark = pytest.mark.django_db


@pytest.fixture
def unit_and_position():
    """A unit Ada holds, and a position held only by Alan, who is deactivated."""
    unit = OrganizationalUnit.objects.create(name="Physics")
    position = OrganizationalPosition.objects.create(name="Researcher")
    Person.objects.create(first_name="Ada", last_name="Lovelace", email="ada@example.org", organizational_unit=unit)
    alan = Person.objects.create(first_name="Alan", last_name="Turing", email="alan@example.org")
    alan.organizational_positions.add(position)
    alan.delete()
    return unit, position


def test_each_has_its_settings_entry_and_list_with_the_active_persons(client, make_user, unit_and_position):
    client.force_login(make_user("organization.view_branding", "core.view_organizationalunit"))
    OrganizationalUnit.objects.create(name="Biology")

    settings_page = client.get(reverse("settings")).content.decode()
    assert f'href="{reverse("organization:unit:index")}"' in settings_page
    assert f'href="{reverse("organization:position:index")}"' not in settings_page
    assert 'id="units"' not in client.get(reverse("organization:branding")).content.decode()

    units = client.get(reverse("organization:unit:index")).context["rows"]
    assert [(unit.name, unit.persons_count) for unit, _cells in units] == [("Biology", 0), ("Physics", 1)]


def test_the_person_forms_plus_adds_one_and_returns_with_it(client, make_user):
    user = make_user("core.add_person", "core.add_organizationalposition")
    client.force_login(user)
    person_form = reverse("persons:add")
    add_url = reverse("organization:position:add")
    assert add_url in client.get(person_form).content.decode()

    response = client.post(
        add_url, {"name": "Head of IT", "next": person_form, "next_field": "organizational_positions"}
    )

    position = OrganizationalPosition.objects.get(name="Head of IT")
    assert position.user == user
    assert response.url == f"{person_form}?organizational_positions={position.pk}"


def test_the_edit_page_links_its_persons(client, make_user, unit_and_position):
    unit, _position = unit_and_position
    client.force_login(make_user("core.view_organizationalunit", "core.view_person"))

    html = client.get(reverse("organization:unit:edit", args=[unit.pk])).content.decode()

    assert f'href="{reverse("persons:index")}?organizational_unit={unit.pk}"' in html


def test_only_an_entry_nobody_holds_is_deleted(client, make_user, unit_and_position):
    unit, position = unit_and_position
    unused = OrganizationalUnit.objects.create(name="Chemistry")
    client.force_login(
        make_user("core.delete_organizationalunit", "core.delete_organizationalposition", "core.view_person")
    )

    response = client.post(reverse("organization:unit:delete", args=[unused.pk]))
    assert response.url == reverse("organization:unit:index")
    assert not OrganizationalUnit.objects.filter(pk=unused.pk).exists()

    # Held by Ada: the page lists her, linked to her page.
    response = client.post(reverse("organization:unit:delete", args=[unit.pk]))
    [persons] = response.context["protected"]
    assert (persons["label"], persons["count"]) == ("Persons", 1)
    assert persons["entries"][0]["url"] == reverse("persons:detail", args=[Person.objects.get(last_name="Lovelace").pk])

    # Held only by deactivated Alan, through the link table: still protected, and
    # the page names him rather than the link table's row.
    response = client.post(reverse("organization:position:delete", args=[position.pk]))
    [persons] = response.context["protected"]
    assert persons["entries"] == [{"label": "Turing, Alan", "url": None, "deactivated": True}]
    assert OrganizationalPosition.objects.filter(pk=position.pk).exists()
