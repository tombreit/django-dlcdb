# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The buttons next to a form's select (``theme.related``)."""

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from dlcdb.core.models import DeviceType, Manufacturer, Room, Supplier
from dlcdb.tenants.models import Tenant
from dlcdb.theme.navigation import with_next
from dlcdb.theme.related import _REGISTRY, add_related_links
from dlcdb.theme.widgets import TomSelectMultipleWidget, TomSelectWidget

FORM_URL = "/assets/devices/7/?next=/assets/devices/"


class _Form(forms.Form):
    manufacturer = forms.ModelChoiceField(Manufacturer.objects.all(), widget=TomSelectWidget(), required=False)
    rooms = forms.ModelMultipleChoiceField(Room.objects.all(), widget=TomSelectMultipleWidget(), required=False)
    # Left alone: a plain select, a picker's hidden input, a model without
    # pages, and a select that is not over a model.
    plain = forms.ModelChoiceField(Manufacturer.objects.all(), required=False)
    picked_room = forms.ModelChoiceField(Room.objects.all(), widget=forms.HiddenInput, required=False)
    tenant = forms.ModelChoiceField(Tenant.objects.all(), widget=TomSelectWidget(), required=False)
    kind = forms.ChoiceField(choices=[("a", "A")], widget=TomSelectWidget(), required=False)


def _form(user, *, data=None, initial=None, **params):
    request = RequestFactory().get(FORM_URL, params) if params else RequestFactory().get(FORM_URL)
    request.user = user
    form = _Form(data=data, initial=initial)
    add_related_links(form, request)
    return form


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(email="admin@example.com", password="secret")


@pytest.fixture
def dell(db):
    return Manufacturer.objects.create(name="Dell")


def test_without_buttons_the_widget_renders_djangos_select():
    widget = TomSelectWidget()

    assert widget.render("x", None).strip() == forms.Select(attrs=widget.attrs).render("x", None).strip()


@pytest.mark.parametrize(
    ("perms", "detail_icon", "has_add"),
    [
        (("core.view_manufacturer",), "bi-eye", False),
        (("core.view_manufacturer", "core.change_manufacturer"), "bi-pencil", False),
        # The detail pages need the view permission, whatever else the user has.
        (("core.change_manufacturer", "core.add_manufacturer"), None, True),
    ],
)
def test_the_buttons_follow_the_related_models_permissions(make_user, dell, perms, detail_icon, has_add):
    html = str(_form(make_user(*perms))["manufacturer"])

    assert "data-related-links" in html
    assert (detail_icon is not None) == ("data-href-template" in html)
    if detail_icon:
        assert detail_icon in html
    assert ("bi-plus-lg" in html) == has_add


def test_without_any_permission_there_are_no_buttons(make_user, dell):
    assert _form(make_user()).fields["manufacturer"].widget.related is None


def test_the_links_return_to_the_form(superuser, dell):
    html = str(_form(superuser, initial={"manufacturer": dell.pk})["manufacturer"])

    detail_url = with_next(reverse("assets:manufacturer_detail", args=[dell.pk]), FORM_URL)
    add_url = with_next(reverse("assets:manufacturer_add") + "?next_field=manufacturer", FORM_URL)
    assert f'href="{detail_url}"' in html
    assert f'href="{add_url.replace("&", "&amp;")}"' in html


def test_the_detail_button_is_disabled_while_nothing_is_selected(superuser, dell):
    html = str(_form(superuser)["manufacturer"])

    template = with_next(reverse("assets:manufacturer_detail", args=[0]), FORM_URL)
    assert f'data-href-template="{template}"' in html
    assert 'aria-disabled="true"' in html


def test_the_detail_button_ignores_a_value_the_select_does_not_offer(superuser, dell):
    # A form re-rendered with a bogus pk, or a stored object the queryset
    # excludes (soft-deleted): nothing is selected, so there is nothing to open.
    html = str(_form(superuser, data={"manufacturer": "999999"})["manufacturer"])

    assert 'aria-disabled="true"' in html
    assert "/manufacturers/999999/" not in html


def test_a_multi_select_gets_only_the_add_button(superuser):
    html = str(_form(superuser)["rooms"])

    assert "bi-plus-lg" in html
    assert "data-href-template" not in html


def test_other_fields_are_left_alone(superuser):
    form = _form(superuser)

    for name in ("plain", "picked_room", "tenant", "kind"):
        assert getattr(form.fields[name].widget, "related", None) is None, name


def test_a_form_re_rendered_after_a_failed_save_counts_as_unsaved(superuser, dell):
    html = str(_form(superuser, data={"manufacturer": "x"})["manufacturer"])

    assert "data-unsaved" in html


def test_the_query_string_preselects_the_new_object(superuser, dell):
    assert _form(superuser, manufacturer=str(dell.pk))["manufacturer"].value() == str(dell.pk)


def test_a_multi_select_adds_the_new_object_to_its_selection(superuser, room_1, room_2):
    form = _form(superuser, initial={"rooms": [room_1]}, rooms=str(room_2.pk))

    assert form["rooms"].value() == [str(room_1.pk), str(room_2.pk)]


@pytest.mark.parametrize("value", ["999999", "Dell", ""])
def test_a_pk_the_select_does_not_offer_is_ignored(superuser, dell, value):
    assert _form(superuser, initial={"manufacturer": dell.pk}, manufacturer=value)["manufacturer"].value() == dell.pk


def test_a_submitted_form_ignores_the_query_string(superuser, dell):
    other = Manufacturer.objects.create(name="Lenovo")

    form = _form(superuser, data={"manufacturer": str(dell.pk)}, manufacturer=str(other.pk))

    assert form["manufacturer"].value() == str(dell.pk)


def test_the_callers_initial_dict_is_not_changed(superuser, dell):
    initial = {}

    _form(superuser, initial=initial, manufacturer=str(dell.pk))

    assert initial == {}


# One object per registered model, for its detail page. A new registration
# fails here until it has one, so the contract below covers every entry.
OBJECTS = {
    "core.devicetype": lambda: DeviceType.objects.create(name="Notebook"),
    "core.manufacturer": lambda: Manufacturer.objects.create(name="Dell"),
    "core.supplier": lambda: Supplier.objects.create(name="Acme"),
    "core.room": lambda: Room.objects.create(number="F1.01"),
}


def test_every_registered_model_has_an_object_here(db):
    assert set(_REGISTRY) == set(OBJECTS)


@pytest.mark.parametrize("label", sorted(OBJECTS))
def test_the_registered_pages_need_exactly_the_permissions_the_buttons_check(client, plain_static, make_user, label):
    """The view permission opens the detail page, the add permission the add page."""
    pages = _REGISTRY[label]
    obj = OBJECTS[label]()
    detail_url = reverse(pages.detail_url, args=[obj.pk])
    add_url = reverse(pages.add_url)

    client.force_login(make_user())
    assert client.get(detail_url).status_code == 403
    assert client.get(add_url).status_code == 403

    client.force_login(make_user(pages.permission("view"), email="viewer@example.com"))
    assert client.get(detail_url).status_code == 200

    client.force_login(make_user(pages.permission("add"), email="adder@example.com"))
    assert client.get(add_url).status_code == 200
