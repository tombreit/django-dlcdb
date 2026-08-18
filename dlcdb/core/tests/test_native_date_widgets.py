# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Native HTML date/time controls must not be localized.

An ``<input type="date">`` reads and submits ISO 8601 whatever the language -- the
browser renders its own locale-aware picker, but the *value* is fixed by the HTML
spec. Django's date widgets render with ``DATE_INPUT_FORMATS[0]`` of the active
locale unless told otherwise, so under "de" a stored date arrives as "14.08.2026",
the browser discards it, shows an empty field and submits it empty: the value is
wiped on save. Django's documented remedy is the widget's ``format`` argument.

This sweeps the declarations, so a form that forgets it fails here even if no test
ever renders it -- admin and create-only forms included.
``test_form_round_trip`` covers the same contract from the rendered-page side.
"""

import importlib
import pkgutil

import pytest
from django import forms
from django.utils import formats, translation

import dlcdb

# The wire format each native control accepts, per the HTML spec. Only "date"
# occurs in this project today; the others are here so the rule stays true if
# someone reaches for them.
NATIVE_INPUT_FORMATS = {
    "date": "%Y-%m-%d",
    "datetime-local": "%Y-%m-%dT%H:%M",
    "time": "%H:%M",
}

RECIPE = 'DateInput(attrs={"type": "date"}, format="%Y-%m-%d")'


def _import_declaring_modules():
    """Import the modules that declare forms, so their classes are registered."""
    for module in pkgutil.walk_packages(dlcdb.__path__, f"{dlcdb.__name__}."):
        name = module.name.rsplit(".", 1)[-1]
        if name in {"forms", "admin"} or name.endswith(("_form", "_forms", "_admin")):
            importlib.import_module(module.name)


def _project_model_forms():
    """Every ModelForm this project declares, however deeply subclassed."""

    def descendants(cls):
        for subclass in cls.__subclasses__():
            yield subclass
            yield from descendants(subclass)

    _import_declaring_modules()
    return sorted(
        {cls for cls in descendants(forms.ModelForm) if cls.__module__.startswith("dlcdb.")},
        key=lambda cls: (cls.__module__, cls.__name__),
    )


def _native_input_type(widget):
    """The native control this widget renders, if any."""
    input_type = getattr(widget, "input_type", None) or widget.attrs.get("type")
    return input_type if input_type in NATIVE_INPUT_FORMATS else None


def test_every_form_is_found():
    """Guard the guard: a sweep that finds nothing would pass silently."""
    form_names = {cls.__name__ for cls in _project_model_forms()}
    assert {"DeviceForm", "LendingForm", "LicenseForm"} <= form_names


@pytest.mark.parametrize("form_class", _project_model_forms(), ids=lambda cls: f"{cls.__module__}.{cls.__name__}")
def test_native_date_widgets_render_iso(form_class):
    for field_name, field in form_class.base_fields.items():
        input_type = _native_input_type(field.widget)
        if not input_type:
            continue
        expected = NATIVE_INPUT_FORMATS[input_type]
        assert field.widget.format == expected, (
            f'{form_class.__name__}.{field_name} renders <input type="{input_type}"> without an ISO '
            f"format, so a localized value is shown and submitted as empty. Use {RECIPE}. "
            "(Setting `format` as a class attribute does not work: DateTimeBaseInput.__init__ "
            "overwrites it.)"
        )


def test_django_still_parses_iso_in_every_locale():
    """The assumption the widget contract rests on.

    Widgets render ISO, so the German locale has to accept ISO on the way back --
    which Django guarantees by appending ISO_INPUT_FORMATS to every locale's list
    (django.utils.formats.get_format). Localized input keeps working too: German
    notation stays first, so "14.08.2026" is still accepted. If a future Django
    drops either half, this test says so instead of the data disappearing.
    """
    with translation.override("de"):
        date_formats = formats.get_format("DATE_INPUT_FORMATS")

    assert date_formats[0] == "%d.%m.%Y", "German input is no longer localized"
    assert "%Y-%m-%d" in date_formats, "ISO is no longer accepted, so native date inputs cannot save"
