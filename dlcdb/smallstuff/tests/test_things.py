# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The smallstuff catalogue (views.ThingViewSet), and with it the pages of
theme.viewsets.ModelViewSet. theme/tests/test_related.py checks the permissions
of its edit and add pages.
"""

import pytest
from django.urls import reverse

from dlcdb.core.models import Person

from ..models import AssignedThing, Thing

pytestmark = pytest.mark.django_db

INDEX = reverse("smallstuff:thing:index")


@pytest.fixture
def webcam():
    """Issued to Ada now; Alan returned his."""
    thing = Thing.objects.create(name="Webcam", slug="webcam")
    ada = Person.objects.create(first_name="Ada", last_name="Lovelace")
    alan = Person.objects.create(first_name="Alan", last_name="Turing")
    AssignedThing.objects.create(person=ada, thing=thing)
    AssignedThing.objects.create(person=alan, thing=thing, unassigned_at="2026-01-01T00:00Z")
    return thing


def test_the_index_lists_the_things_with_the_number_issued(client, make_user, webcam):
    Thing.objects.create(name="Mouse", slug="mouse")
    client.force_login(make_user("smallstuff.view_thing"))

    response = client.get(INDEX)
    assert [(row.name, row.issued) for row, _cells in response.context["rows"]] == [("Mouse", 0), ("Webcam", 1)]
    assert reverse("smallstuff:thing:add") not in response.content.decode()

    response = client.get(INDEX, {"search": "cam", "ordering": "-issued"}, headers={"HX-Request": "true"})
    assert [row.name for row, _cells in response.context["rows"]] == ["Webcam"]
    assert 'id="object-list"' in response.content.decode()


def test_the_index_needs_the_view_permission(client, make_user):
    client.force_login(make_user("smallstuff.view_assignedthing"))
    assert client.get(INDEX).status_code == 403


def test_adding_stamps_the_user_and_fills_the_slug(client, make_user):
    user = make_user("smallstuff.add_thing", "smallstuff.view_thing")
    client.force_login(user)

    response = client.post(reverse("smallstuff:thing:add"), {"name": "USB Hub"})

    thing = Thing.objects.get(name="USB Hub")
    assert (thing.slug, thing.user) == ("usb-hub", user)
    assert response.url == reverse("smallstuff:thing:edit", args=[thing.pk])


def test_a_name_with_the_slug_of_another_is_refused(client, make_user, webcam):
    client.force_login(make_user("smallstuff.view_thing", "smallstuff.change_thing"))
    other = Thing.objects.create(name="Mouse", slug="mouse")

    response = client.post(reverse("smallstuff:thing:edit", args=[other.pk]), {"name": "Webcam!"})
    assert response.status_code == 200 and response.context["form"].errors["name"]

    response = client.post(reverse("smallstuff:thing:edit", args=[other.pk]), {"name": "Mouse (USB)"}, follow=True)
    other.refresh_from_db()
    assert (other.name, other.slug) == ("Mouse (USB)", "mouse-usb")
    link = f'<a href="{reverse("smallstuff:thing:edit", args=[other.pk])}">Mouse (USB)</a>'
    assert any(link in str(message) for message in response.context["messages"])


def test_the_edit_page_lists_the_holders_and_is_read_only_without_the_change_permission(client, make_user, webcam):
    client.force_login(make_user("smallstuff.view_thing"))

    response = client.get(reverse("smallstuff:thing:edit", args=[webcam.pk]))

    assert [str(assignment.person) for assignment in response.context["holders"]] == ["Lovelace, Ada"]
    assert response.context["form"].fields["name"].disabled
    assert response.context["delete_url"] is None


def test_only_a_thing_never_handed_out_is_deleted(client, make_user, webcam):
    client.force_login(make_user("smallstuff.delete_thing"))
    unused = Thing.objects.create(name="Mouse", slug="mouse")

    response = client.post(reverse("smallstuff:thing:delete", args=[unused.pk]))
    assert response.url == INDEX
    assert not Thing.objects.filter(pk=unused.pk).exists()

    # Returned by everyone but Ada: still protected, also against a direct POST.
    AssignedThing.objects.filter(unassigned_at__isnull=True).update(unassigned_at="2026-02-01T00:00Z")
    assert client.get(reverse("smallstuff:thing:delete", args=[webcam.pk])).context["protected"]
    response = client.post(reverse("smallstuff:thing:delete", args=[webcam.pk]))
    assert response.status_code == 200 and response.context["protected"]
    assert Thing.objects.filter(pk=webcam.pk).exists()


def test_the_settings_entry_opens_the_catalogue_without_the_staff_flag(client, make_user):
    client.force_login(make_user("smallstuff.view_thing"))

    response = client.get(reverse("settings"))

    assert f'href="{INDEX}"' in response.content.decode()
