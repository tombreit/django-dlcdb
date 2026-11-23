# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending profiles (views_profiles.LendingProfileViewSet): what differs from
any ModelViewSet. smallstuff/tests/test_things.py covers the rest.
"""

import pytest
from django.urls import reverse

from dlcdb.core.models import DeviceType, Link
from dlcdb.lending.models import SCRIPT_RE, LendingProfile
from dlcdb.lending.starter import get_starter_lending_preparation_checklist, get_starter_lent_sheet_template

pytestmark = pytest.mark.django_db

CONFIG = "lending.view_lendingconfiguration"
VIEW = "lending.view_lendingprofile"
ADD = "lending.add_lendingprofile"
CHANGE = "lending.change_lendingprofile"
DELETE = "lending.delete_lendingprofile"


@pytest.fixture
def login(client, make_user):
    def _login(*perms):
        client.force_login(make_user(*perms))
        return client

    return _login


@pytest.fixture
def laptop():
    return DeviceType.objects.create(name="Laptop")


@pytest.fixture
def profile(laptop):
    return LendingProfile.objects.create(device_type=laptop, lent_sheet_template="slip")


def _post_data(device_type, **fields):
    return {"device_type": device_type.pk, "lent_sheet_template": "slip", "lending_preparation_checklist": "", **fields}


@pytest.mark.parametrize(("perms", "listed"), [((CONFIG,), False), ((CONFIG, VIEW), True)])
def test_settings_lists_the_profiles_with_their_view_permission(login, profile, perms, listed):
    response = login(*perms).get(reverse("settings"))

    assert (f'href="{reverse("lending:profile:index")}"' in response.content.decode()) == listed


def test_a_profile_is_added_for_the_preselected_device_type(login, laptop):
    client = login(ADD)
    rules = Link.objects.create(linktext="IT rules", url="https://example.org/rules")

    form = client.get(reverse("lending:profile:add"), {"device_type": laptop.pk}).context["form"]
    response = client.post(
        f"{reverse('lending:profile:add')}?device_type={laptop.pk}",
        _post_data(laptop, mandatory_regulations=[rules.pk]),
    )

    assert form["device_type"].value() == str(laptop.pk)
    profile = LendingProfile.objects.get(device_type=laptop)
    assert response.url == reverse("lending:profile:edit", args=[profile.pk])
    assert list(profile.mandatory_regulations.all()) == [rules]


def test_only_device_types_without_a_profile_are_offered(login, profile):
    tablet = DeviceType.objects.create(name="Tablet")
    DeviceType.objects.create(name="Phone")
    LendingProfile.objects.create(device_type=DeviceType.objects.get(name="Phone"))

    response = login(VIEW, CHANGE).get(reverse("lending:profile:edit", args=[profile.pk]))

    assert set(response.context["form"].fields["device_type"].queryset) == {profile.device_type, tablet}


def test_a_profile_keeps_its_deactivated_device_type(login, profile):
    profile.device_type.delete()  # deactivates
    DeviceType.objects.create(name="Pager").delete()
    client = login(VIEW, CHANGE)
    url = reverse("lending:profile:edit", args=[profile.pk])

    choices = client.get(url).context["form"].fields["device_type"].queryset
    response = client.post(url, _post_data(profile.device_type, lent_sheet_template="new slip"))

    assert list(choices) == [profile.device_type]
    assert response.status_code == 302
    profile.refresh_from_db()
    assert profile.lent_sheet_template == "new slip"


@pytest.mark.parametrize("field", ["lent_sheet_template", "lending_preparation_checklist"])
@pytest.mark.parametrize(
    "script",
    ["<script>alert(1)</script>", '<img src="x" onerror="alert(1)">', '<a href="JavaScript:alert(1)">x</a>'],
)
def test_saving_refuses_scripts(login, profile, field, script):
    response = login(VIEW, CHANGE).post(
        reverse("lending:profile:edit", args=[profile.pk]), _post_data(profile.device_type, **{field: script})
    )

    assert response.status_code == 200
    assert field in response.context["form"].errors


def test_the_starter_content_has_no_script():
    assert not SCRIPT_RE.search(get_starter_lent_sheet_template())
    assert not SCRIPT_RE.search(get_starter_lending_preparation_checklist())


def test_an_emptied_slip_template_gets_the_starter_content_again(login, profile):
    response = login(VIEW, CHANGE).post(
        reverse("lending:profile:edit", args=[profile.pk]),
        _post_data(profile.device_type, lent_sheet_template=""),
        follow=True,
    )

    profile.refresh_from_db()
    assert profile.lent_sheet_template == get_starter_lent_sheet_template()
    assert any("starter content" in str(message) for message in response.context["messages"])


def test_on_a_profile_page_its_settings_entry_is_active(login, profile):
    response = login(CONFIG, VIEW, "core.view_lentrecord").get(reverse("lending:profile:edit", args=[profile.pk]))

    active = [
        item["url"]
        for item in response.context["nav_items_main"] + response.context["nav_items_settings"]
        if item["active"]
    ]
    assert active == ["lending:profile:index"]


def test_the_field_history_shows_who_changed_the_slip_template(login, profile):
    client = login(VIEW, CHANGE)
    client.post(
        reverse("lending:profile:edit", args=[profile.pk]), _post_data(profile.device_type, lent_sheet_template="v2")
    )

    entries = client.get(reverse("lending:profile:history", args=[profile.pk])).context["entries"]

    latest = entries[0]
    assert latest.user.email == "user@example.com"
    assert [(change.field, change.old, change.new) for change in latest.changes] == [
        ("Lending slip template", "slip", "v2")
    ]


def test_the_field_history_needs_the_view_permission(login, profile):
    assert login(CONFIG).get(reverse("lending:profile:history", args=[profile.pk])).status_code == 403


def test_a_deleted_profile_is_gone_and_the_page_returns_to_the_list(login, profile):
    response = login(DELETE).post(reverse("lending:profile:delete", args=[profile.pk]))

    assert response.url == reverse("lending:profile:index")
    assert not LendingProfile.objects.exists()
