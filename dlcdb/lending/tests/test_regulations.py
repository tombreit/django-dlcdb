# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending regulations (views_profiles.RegulationViewSet): what differs from
any ModelViewSet. smallstuff/tests/test_things.py covers the rest.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from dlcdb.core.models import DeviceType, Link
from dlcdb.lending.models import LendingProfile

pytestmark = pytest.mark.django_db

ADD = "core.add_link"


@pytest.fixture
def rules():
    """Required by the laptops' lending profile."""
    link = Link.objects.create(linktext="IT rules", url="https://example.org/rules")
    profile = LendingProfile.objects.create(device_type=DeviceType.objects.create(name="Laptop"))
    profile.mandatory_regulations.add(link)
    return link


def test_a_regulation_is_a_file_or_a_url(client, make_user, media_root):
    client.force_login(make_user(ADD, "core.view_link"))
    add_url = reverse("lending:regulation:add")

    response = client.post(add_url, {"linktext": "Loan terms"})
    assert response.status_code == 200 and response.context["form"].non_field_errors()

    pdf = SimpleUploadedFile("terms.pdf", b"%PDF-1.4", content_type="application/pdf")
    client.post(add_url, {"linktext": "Loan terms", "file": pdf})
    assert Link.objects.get(linktext="Loan terms").file.name == "links/terms.pdf"
    assert (media_root / "links" / "terms.pdf").exists()


def test_the_list_counts_the_profiles_that_require_it(client, make_user, rules):
    Link.objects.create(linktext="Old rules", url="https://example.org/old")
    client.force_login(make_user("core.view_link"))

    rows = client.get(reverse("lending:regulation:index")).context["rows"]

    assert [(link.linktext, link.profiles) for link, _cells in rows] == [("IT rules", 1), ("Old rules", 0)]


def test_one_a_profile_requires_is_not_deleted_and_the_page_names_the_profile(client, make_user, rules):
    unused = Link.objects.create(linktext="Old rules", url="https://example.org/old")
    client.force_login(make_user("core.delete_link", "lending.view_lendingprofile"))

    response = client.post(reverse("lending:regulation:delete", args=[rules.pk]))
    [profiles] = response.context["protected"]
    assert (profiles["label"], profiles["entries"][0]["label"]) == ("Lending profiles", "Laptop")
    assert Link.objects.filter(pk=rules.pk).exists()

    client.post(reverse("lending:regulation:delete", args=[unused.pk]))
    assert not Link.objects.filter(pk=unused.pk).exists()


def test_the_lending_profile_form_can_add_a_regulation(client, make_user):
    client.force_login(make_user("lending.add_lendingprofile", ADD))

    html = client.get(reverse("lending:profile:add")).content.decode()

    assert reverse("lending:regulation:add") in html


def test_the_settings_entry_opens_the_list_without_the_staff_flag(client, make_user):
    client.force_login(make_user("core.view_link"))

    html = client.get(reverse("settings")).content.decode()

    assert f'href="{reverse("lending:regulation:index")}"' in html
