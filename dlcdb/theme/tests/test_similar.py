# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The duplicate check of the add pages (``theme.similar``), on names like the production data's."""

import pytest

from dlcdb.core.models import Manufacturer, Person, Room, Supplier
from dlcdb.theme.similar import COMPANY_NOISE_WORDS, SimilarNames, find_similar, words

COMPANIES = SimilarNames(fields=("name",), noise_words=COMPANY_NOISE_WORDS)
ROOMS = SimilarNames(fields=("number",), fuzzy=False)
PERSONS = SimilarNames(fields=("last_name", "first_name"))


def test_words_ignore_case_umlauts_accents_punctuation_and_noise_words():
    assert words("KÄRCHER") == words("Kärcher") == ["kaercher"]
    assert words("Straße") == ["strasse"]
    assert words("Café-Bar") == ["cafe", "bar"]
    assert words("Dell Inc.", COMPANY_NOISE_WORDS) == ["dell"]
    # Decomposed and composed umlauts are the same letter.
    assert words("Müller") == words("Müller")


@pytest.mark.django_db
@pytest.mark.parametrize("existing", ["Procom", "procom", "pro-com", "PROCOM GmbH"])
def test_other_spellings_of_a_name_are_identical(existing):
    supplier = Supplier.objects.create(name=existing)

    assert find_similar(Supplier, COMPANIES, {"name": "Procom"}).identical == [supplier]


@pytest.mark.django_db
def test_umlaut_and_its_transcription_are_identical():
    person = Person.objects.create(first_name="Max", last_name="Müller", email="max@example.com")

    assert find_similar(Person, PERSONS, {"last_name": "Mueller", "first_name": "MAX"}).identical == [person]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("existing", "new"),
    [
        ("Pulse Secure", "Pulse"),  # the words of one are among the other's
        ("Lenovo", "Lenvoo"),  # a typo
        ("Procom", "Pro"),  # the start of an existing name, as while typing
    ],
)
def test_similar_names_are_similar_not_identical(existing, new):
    manufacturer = Manufacturer.objects.create(name=existing)

    matches = find_similar(Manufacturer, COMPANIES, {"name": new})

    assert matches.identical == []
    assert matches.similar == [manufacturer]


@pytest.mark.django_db
def test_unrelated_names_do_not_match():
    Manufacturer.objects.create(name="Apple")

    assert not find_similar(Manufacturer, COMPANIES, {"name": "Dell"})


@pytest.mark.django_db
def test_room_numbers_match_only_when_identical():
    room = Room.objects.create(number="F1.01")

    assert find_similar(Room, ROOMS, {"number": "f 1.01"}).identical == [room]
    # The room next door looks alike, but is another room; so does a number
    # being typed.
    assert not find_similar(Room, ROOMS, {"number": "F1.02"})
    assert not find_similar(Room, ROOMS, {"number": "F1.0"})


@pytest.mark.django_db
def test_a_deactivated_entry_counts():
    room = Room.objects.create(number="F1.01")
    room.delete()

    assert find_similar(Room, ROOMS, {"number": "F1.01"}).identical == [room]


@pytest.mark.django_db
def test_similar_entries_come_best_first():
    # Contains the name, but is much longer: a lower ratio than the typo.
    distant = Manufacturer.objects.create(name="Lenovo Thinkpad")
    close = Manufacturer.objects.create(name="Lenvoo")

    assert find_similar(Manufacturer, COMPANIES, {"name": "Lenovo"}).similar == [close, distant]


@pytest.mark.django_db
def test_an_empty_name_matches_nothing():
    Manufacturer.objects.create(name="Dell")

    assert not find_similar(Manufacturer, COMPANIES, {"name": " - "})
