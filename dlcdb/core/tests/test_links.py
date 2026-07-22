# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Objects named in a Django message are rendered as links to their detail views."""

import pytest

from django.urls import reverse
from django.utils.safestring import SafeString

from dlcdb.core.models import Device, Person, Room
from dlcdb.core.utils.links import linked_message, obj_link


@pytest.mark.django_db
def test_obj_link_device():
    device = Device.objects.create(edv_id="EDV-1")
    url = reverse("assets:device_detail", args=[device.pk])
    assert obj_link(device) == f'<a href="{url}">EDV-1</a>'


@pytest.mark.django_db
def test_obj_link_licence_uses_its_own_form():
    """A licence has no device detail page; get_absolute_url() points at its form."""
    licence = Device.objects.create(edv_id="LIC-1", is_licence=True)
    url = reverse("licenses:edit", kwargs={"license_id": licence.pk})
    assert obj_link(licence) == f'<a href="{url}">LIC-1</a>'


@pytest.mark.django_db
def test_obj_link_room_and_person():
    room = Room.objects.create(number="235", nickname="Breitner, Gies")
    person = Person.objects.create(first_name="Thomas", last_name="Breitner")

    assert obj_link(room) == f'<a href="{reverse("rooms:detail", args=[room.pk])}">235 (Breitner, Gies)</a>'
    assert obj_link(person) == f'<a href="{reverse("persons:detail", args=[person.pk])}">Breitner, Thomas</a>'


@pytest.mark.django_db
def test_obj_link_label_overrides_the_anchor_text():
    device = Device.objects.create(edv_id="EDV-1")
    url = reverse("assets:device_detail", args=[device.pk])
    assert obj_link(device, label="Acme - X1") == f'<a href="{url}">Acme - X1</a>'


def test_obj_link_of_a_non_linkable_value_is_escaped_text():
    """Anything that is not a Device/Room/Person is escaped, not linked."""
    assert obj_link("Tenant <A>") == "Tenant &lt;A&gt;"
    assert obj_link(None) == "None"
    # An unsaved model instance has no pk to reverse with.
    assert obj_link(Room(number="A1.01")) == "A1.01"


@pytest.mark.django_db
def test_anchor_text_is_escaped():
    device = Device.objects.create(edv_id="<script>alert(1)</script>")
    rendered = obj_link(device)
    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


@pytest.mark.django_db
def test_linked_message_substitutes_links_and_stays_safe():
    device = Device.objects.create(edv_id="SON60000895")
    room = Room.objects.create(number="235", nickname="Breitner, Gies")

    msg = linked_message("Device “{device}” moved to room “{room}”.", device=device, room=room)

    assert isinstance(msg, SafeString)
    assert f'<a href="{reverse("assets:device_detail", args=[device.pk])}">SON60000895</a>' in msg
    assert f'<a href="{reverse("rooms:detail", args=[room.pk])}">235 (Breitner, Gies)</a>' in msg
    assert msg.startswith("Device “<a")


@pytest.mark.django_db
def test_linked_message_escapes_plain_parts():
    device = Device.objects.create(edv_id="EDV-1")
    msg = linked_message("Device {device}: Set new tenant to {tenant}.", device=device, tenant="<b>T</b>")
    assert "&lt;b&gt;T&lt;/b&gt;" in msg


@pytest.mark.django_db
def test_linked_message_needs_literal_braces_doubled():
    """The message is a str.format template, so a literal brace must be doubled."""
    device = Device.objects.create(edv_id="EDV-1")
    assert linked_message("Device {device} {{tagged}}.", device=device).endswith("{tagged}.")
