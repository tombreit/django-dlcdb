# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
One guard for the whole class of "opening a page and saving it loses data".

Every frontend edit page must satisfy three invariants:

a. every field the form declares is actually rendered -- an unrendered field is
   not submitted, and Django writes the empty value back over the stored one;
b. every ``<input type="date">`` carries an ISO value -- a browser refuses to
   display any other notation, shows an empty field and submits it empty;
c. posting the page back unchanged changes nothing in the database.

(a) and (c) are two sides of the same coin, but they fail differently and (a)
names the culprit field, so both are asserted.

The pages are exercised under German: production runs ``de-de`` while the suite
defaults to ``en`` (dlcdb/settings/test.py), and the locale used to decide how a
widget renders its value is exactly where this class of bug hides.
"""

import datetime
from dataclasses import dataclass
from typing import Callable

import pytest
from django.urls import reverse

from dlcdb.accounts.models import CustomUser
from dlcdb.core.models import (
    Device,
    DeviceType,
    LentRecord,
    Manufacturer,
    OrganizationalUnit,
    Person,
    Room,
    Supplier,
)
from dlcdb.core.tests.formcheck import ISO_DATE_RE, date_input_values, rendered_input_names
from dlcdb.core.tests.testingutils import establish_state
from dlcdb.tenants.models import Tenant

pytestmark = pytest.mark.django_db

GERMAN = {"accept-language": "de"}

# Written by the save path itself, not by the form: they are expected to change.
AUDIT_FIELDS = {"user", "username", "modified_at"}


@dataclass(frozen=True)
class EditPage:
    """One edit page, its fully populated subject and what may change on save."""

    label: str
    build: Callable[[], tuple[str, object]]  # -> (url, instance)
    # A page whose POST is a state change by design (returning a lending) cannot
    # assert (c); it still has to render and round-trip its values honestly.
    idempotent: bool = True


def _snapshot(obj, exclude):
    """Every stored value of ``obj``, as plain comparable data."""
    obj.refresh_from_db()
    return {f.name: f.value_from_object(obj) for f in obj._meta.fields if f.name not in exclude}


def _person(email="ada.lovelace@example.com", last_name="Lovelace"):
    return Person.objects.create(
        first_name="Ada",
        last_name=last_name,
        email=email,
        organizational_unit=OrganizationalUnit.objects.get_or_create(name="Mathematics")[0],
    )


def _populated_device(**overrides):
    """A device with *every* DeviceForm field filled, so a wipe cannot hide."""
    values = dict(
        edv_id="EDV-ROUNDTRIP",
        sap_id="1234567-0",
        device_type=DeviceType.objects.create(name="Notebook", prefix="NTB"),
        manufacturer=Manufacturer.objects.create(name="Example Inc."),
        supplier=Supplier.objects.create(name="IT Supplies Ltd.", contact="sales@example.com"),
        tenant=Tenant.objects.create(name="RoundTripTenant"),
        contact_person_internal=_person(),
        series="ExampleBook 14",
        serial_number="SN-2026-0001",
        note="A note",
        procurement_note="A procurement note",
        order_number="PO-2026-001",
        cost_centre="4711",
        book_value="1499.00",
        purchase_date=datetime.date(2026, 1, 15),
        warranty_expiration_date=datetime.date(2029, 1, 15),
        contract_start_date=datetime.date(2026, 1, 15),
        contract_expiration_date=datetime.date(2029, 1, 15),
        contract_termination_date=datetime.date(2030, 1, 15),
        url="https://example.com/device",
        nick_name="notebook-01",
        mac_address="00:11:22:33:44:55",
        extra_mac_addresses="00:11:22:33:44:56",
        machine_encryption_key="machine-key",
        backup_encryption_key="backup-key",
        is_lentable=True,
        is_licence=False,
    )
    values.update(overrides)
    return Device.objects.create(**values)


def _device_page():
    device = _populated_device()
    return reverse("assets:device_detail", args=[device.pk]), device


def _device_type_page():
    device_type = DeviceType.objects.create(name="Monitor", prefix="MON", icon="bi-display", note="A note")
    return reverse("assets:device_type_detail", args=[device_type.pk]), device_type


def _manufacturer_page():
    manufacturer = Manufacturer.objects.create(name="Example Inc.", note="A note")
    return reverse("assets:manufacturer_detail", args=[manufacturer.pk]), manufacturer


def _supplier_page():
    supplier = Supplier.objects.create(name="IT Supplies Ltd.", contact="sales@example.com", note="A note")
    return reverse("assets:supplier_detail", args=[supplier.pk]), supplier


def _lent_record():
    device = _populated_device(edv_id="EDV-LENT", sap_id="1234567-1")
    # A lending cannot validate without the room a returned device goes back to.
    Room.objects.create(number="RETURN", is_auto_return_room=True)
    return establish_state(
        LentRecord,
        device=device,
        room=Room.objects.create(number="355", nickname="Lab"),
        person=_person("lent.to@example.com", last_name="Byron"),
        lent_start_date=datetime.date(2026, 1, 15),
        lent_desired_end_date=datetime.date(2026, 6, 15),
        lent_reason="Home office",
        lent_accessories="Charger, case",
        lent_note="A note",
        sync_lent_end_date=True,
    )


def _lending_edit_page():
    record = _lent_record()
    return reverse("lending:detail", args=[record.pk]), record


def _lending_return_page():
    record = _lent_record()
    return f"{reverse('lending:detail', args=[record.pk])}?flow=return", record


def _license_page():
    # The form limits the device type choices to the license prefixes, so the
    # stored type has to be one of them or it cannot round-trip.
    license_type = DeviceType.objects.create(name="Lizenz::Software", prefix="LIC")
    device = _populated_device(
        edv_id="EDV-LICENCE",
        sap_id="1234567-2",
        device_type=license_type,
        is_licence=True,
    )
    return reverse("licenses:edit", args=[device.pk]), device


def _person_page():
    person = _person("person.page@example.com", last_name="Noether")
    return reverse("persons:detail", args=[person.pk]), person


def _room_page():
    room = Room.objects.create(
        number="A1.01",
        nickname="Lab",
        description="A description",
        website="https://example.com/room",
        note="A note",
        is_auto_return_room=True,
        is_external=False,
        is_default_license_room=True,
    )
    return reverse("rooms:detail", args=[room.pk]), room


EDIT_PAGES = [
    EditPage("device", _device_page),
    EditPage("device_type", _device_type_page),
    EditPage("manufacturer", _manufacturer_page),
    EditPage("supplier", _supplier_page),
    EditPage("lending_edit", _lending_edit_page),
    # Returning a lending ends it on purpose (lending/views.py, transition_return_lending),
    # so only the render-side invariants apply.
    EditPage("lending_return", _lending_return_page, idempotent=False),
    EditPage("license", _license_page),
    EditPage("person", _person_page),
    # Room.save() deliberately clears is_auto_return_room/is_external on *other*
    # rooms; the snapshot covers the edited row only, so that stays out of scope.
    EditPage("room", _room_page),
]

# Not covered: inventory:note-update. Its form has a single field and reaching it
# needs an active inventory plus a note already attached to the object, so the
# setup would outweigh what the guard could learn. Add it if the form grows.


@pytest.fixture
def editor_client(client, db):
    """A client that may open and save every page in the registry."""
    user = CustomUser.objects.create_superuser(
        email="editor@example.com",
        password="secret",
        username="roundtrip-editor",
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize("page", EDIT_PAGES, ids=lambda page: page.label)
def test_edit_page_renders_and_round_trips_every_field(page, editor_client, plain_static):
    url, obj = page.build()
    before = _snapshot(obj, AUDIT_FIELDS)

    response = editor_client.get(url, headers=GERMAN)
    assert response.status_code == 200
    html = response.content.decode()
    form = response.context["form"]

    # (a) A field the page does not render is a field the next save deletes.
    unrendered = set(form.fields) - rendered_input_names(html)
    assert not unrendered, f"{page.label}: not rendered, so wiped on save: {sorted(unrendered)}"

    # (b) A non-ISO value in a date input is shown -- and submitted -- as empty.
    for name, value in date_input_values(html):
        assert value == "" or ISO_DATE_RE.fullmatch(value), f"{page.label}: {name} renders non-ISO {value!r}"

    # (c) Saving the page as it was rendered must not change anything. The payload
    # is restricted to what the page actually carries, which is what makes this a
    # round trip rather than a replay of the form object.
    rendered = rendered_input_names(html)
    payload = {name: form[name].value() for name in form.fields if name in rendered}
    post_response = editor_client.post(url, payload, headers=GERMAN)
    # A rejected save would leave the row untouched and make (c) pass for the
    # wrong reason, so insist the page actually saved and redirected.
    if post_response.status_code != 302:
        errors = post_response.context["form"].errors if post_response.context else "no form in context"
        pytest.fail(f"{page.label}: saving the unchanged page was rejected: {errors}")

    if page.idempotent:
        assert _snapshot(obj, AUDIT_FIELDS) == before
