# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Settings › Organization: the units and positions persons hold (views_masterdata.py)."""

import pytest
from django.urls import reverse

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit, Person

pytestmark = pytest.mark.django_db

PAGE = reverse("organization:branding")


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


def test_each_card_lists_its_entries_with_their_active_persons(client, make_user, unit_and_position):
    client.force_login(make_user("organization.view_branding", "core.view_organizationalunit"))
    OrganizationalUnit.objects.create(name="Biology")

    response = client.get(PAGE)

    html = response.content.decode()
    assert 'id="units"' in html and 'href="#units"' in html
    assert 'id="positions"' not in html and 'href="#positions"' not in html
    assert [(unit.name, unit.persons_count) for unit in response.context["units"]] == [("Biology", 0), ("Physics", 1)]
    assert {position.name: position.persons_count for position in response.context["positions"]} == {"Researcher": 0}


def test_adding_and_saving_return_to_its_card(client, make_user):
    user = make_user(
        "core.add_organizationalposition", "core.view_organizationalposition", "core.change_organizationalposition"
    )
    client.force_login(user)

    response = client.post(reverse("organization:position_add"), {"name": "Head of IT"})
    assert response.url == f"{PAGE}#positions"
    position = OrganizationalPosition.objects.get(name="Head of IT")
    assert position.user == user

    detail_url = reverse("organization:position_detail", args=[position.pk])
    response = client.post(detail_url, {"name": "Head of IT services"}, follow=True)
    assert response.redirect_chain == [(f"{PAGE}#positions", 302)]
    link = f'<a href="{detail_url}">Head of IT services</a>'
    assert any(link in str(message) for message in response.context["messages"])


def test_only_an_entry_nobody_holds_is_deleted(client, make_user, unit_and_position):
    _unit, position = unit_and_position
    unused = OrganizationalUnit.objects.create(name="Chemistry")
    client.force_login(make_user("core.delete_organizationalunit", "core.delete_organizationalposition"))

    response = client.post(reverse("organization:unit_delete", args=[unused.pk]))
    assert response.url == f"{PAGE}#units"
    assert not OrganizationalUnit.objects.filter(pk=unused.pk).exists()

    # Held by a deactivated person only: still protected, and the page says by whom.
    response = client.post(reverse("organization:position_delete", args=[position.pk]))
    assert response.status_code == 200
    assert (response.context["persons_count"], response.context["deactivated_count"]) == (0, 1)
    assert OrganizationalPosition.objects.filter(pk=position.pk).exists()


def test_the_person_form_can_add_a_unit_and_a_position(client, make_user):
    client.force_login(make_user("core.add_person", "core.add_organizationalunit", "core.add_organizationalposition"))

    html = client.get(reverse("persons:add")).content.decode()

    assert reverse("organization:unit_add") in html
    assert reverse("organization:position_add") in html
