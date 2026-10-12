# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
What makes a person match a search term (``Person.search_q``): first name, last name or
email address, ignoring case, directly or through a relation.
"""

import datetime

import pytest

from dlcdb.core.models import Device, LentRecord, Person, Record, Room
from dlcdb.core.tests.testingutils import establish_state


@pytest.fixture
def people(db):
    return {
        "max": Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.com"),
        "erika": Person.objects.create(
            first_name="Erika", last_name="Musterfrau", email="e.m@example.org", udb_person_last_name="Gabler"
        ),
    }


@pytest.mark.parametrize(
    "term, expected",
    [
        ("ERIKA", {"erika"}),
        ("mustermann", {"max"}),
        ("example.org", {"erika"}),
        ("muster", {"max", "erika"}),
        # The UDB-mirrored names are the persons list's own addition.
        ("gabler", set()),
    ],
)
def test_first_name_last_name_or_email_match_ignoring_case(people, term, expected):
    assert set(Person.objects.filter(Person.search_q(term))) == {people[key] for key in expected}


def test_the_prefix_reaches_the_person_through_a_relation(people, tenant):
    lending = establish_state(
        LentRecord,
        device=Device.objects.create(edv_id="EDV-1", is_lentable=True, tenant=tenant),
        person=people["erika"],
        room=Room.objects.create(number="A1.23"),
        lent_start_date=datetime.date(2026, 1, 1),
        lent_desired_end_date=datetime.date(2026, 12, 31),
    )

    assert list(Record.objects.filter(Person.search_q("erika", prefix="person__"))) == [lending]
