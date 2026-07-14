# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json

from django import forms
from django.utils.translation import gettext_lazy as _

from .bootstrap_icons import get_bootstrap_icons
from .pickers import get_picker_source


class TomSelectWidget(forms.Select):
    """
    Searchable single-select, enhanced client-side by ``theme.js``.

    Emits the ``is-tom-select`` contract (alongside Bootstrap's ``form-select``)
    plus the ``data-placeholder`` / ``data-clear-button`` hints that
    ``theme.js`` reads (see ``initTomSelect`` in
    ``theme/assets/js/theme.js``): ``data-clear-button`` opts a single-select
    into the ``clear_button`` plugin (one "clear all" control) instead of a
    per-tag ``remove_button``, and ``data-placeholder`` replaces the empty
    option's ``---------`` label with a greyed hint.

    Intentionally ships NO ``Media`` and NO ``template_name`` — unlike the
    picker widgets below. TomSelect's JS/CSS are bundled once into the global
    theme bundle loaded by ``theme/_base.html`` on every page, and Django's
    default ``<select>`` template renders fine (TomSelect enhances it in the
    browser). Adding a per-widget ``Media`` here would double-load TomSelect,
    so do not "fix" this by adding one.
    """

    def __init__(self, attrs=None, *, placeholder=None):
        defaults = {
            "class": "form-select is-tom-select",
            "data-placeholder": placeholder or _("Type to search…"),
            "data-clear-button": "true",  # single select -> clear_button plugin
        }
        super().__init__(_merge_tom_select_attrs(defaults, attrs))


class TomSelectMultipleWidget(forms.SelectMultiple):
    """
    Searchable multi-select counterpart to :class:`TomSelectWidget`.

    Same ``is-tom-select`` contract, but no ``data-clear-button``: a
    multi-select reads better with the default per-tag ``remove_button``
    plugin. See :class:`TomSelectWidget` for why this widget carries no
    ``Media``/``template_name``.
    """

    def __init__(self, attrs=None, *, placeholder=None):
        defaults = {
            "class": "form-select is-tom-select",
            "data-placeholder": placeholder or _("Type to search…"),
        }
        super().__init__(_merge_tom_select_attrs(defaults, attrs))


def _merge_tom_select_attrs(defaults, attrs):
    """Merge caller ``attrs`` over ``defaults``, appending (not clobbering) class."""
    merged = {**defaults, **(attrs or {})}
    extra_class = (attrs or {}).get("class")
    if extra_class:
        merged["class"] = f"{defaults['class']} {extra_class}"
    return merged


class IconPickerWidget(forms.TextInput):
    """
    Text input augmented with a searchable Bootstrap Icons picker.

    The stored value stays a plain ``bi-<name>`` class string, so the field
    behaves like a normal text input (manual entry still works); the picker is
    a visual assist. The icon set is the one currently installed (see
    ``dlcdb.theme.bootstrap_icons.get_bootstrap_icons``), so it tracks
    package upgrades automatically.
    """

    template_name = "theme/widgets/icon_picker.html"

    class Media:
        css = {"all": ["theme/widgets/iconpicker.css"]}
        js = ["theme/widgets/iconpicker.js"]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        icons = get_bootstrap_icons()

        # ensure_ascii keeps the PUA glyphs as \uXXXX escapes — safe inside the
        # <script type="application/json"> block.
        context["widget"]["icons_json"] = json.dumps(icons)

        current = (value or "").strip().removeprefix("bi-")
        context["widget"]["current_char"] = next((icon["char"] for icon in icons if icon["name"] == current), "")
        return context


class DevicePickerWidget(forms.Widget):
    """
    Centralized device picker: an HTMX live-search + selectable-card UI that
    writes the chosen ``core.Device`` pk(s) into a hidden form field.

    The widget is generic — it only ever deals with devices. A ``source`` (a
    ``theme.pickers.PickerSource`` registered by the owning app) selects which
    devices the live search offers and which permission guards it; the source is
    resolved lazily by name so the registry need not be populated at import time.

    Rendering of the pre-selected card(s) (e.g. after a validation error) uses
    Django's own machinery: a bound ``ModelChoiceField``/``ModelMultipleChoiceField``
    installs its (tenant-scoped) queryset on ``self.choices``; we resolve the
    submitted pk(s) straight from ``self.choices.queryset`` — no bespoke object
    resolver, and tenant-safe because it is the same queryset used for validation.
    Pair it with :class:`DevicePickerField` / :class:`DevicePickerMultiField`.
    """

    template_name = "theme/widgets/device_picker/widget.html"

    # picker_id seeds all DOM ids (``device-search-input`` etc.) and the per-page
    # glue JS keys off these, so there is one device picker per page.
    picker_id = "device"

    class Media:
        css = {"all": ["theme/widgets/picker.css"]}
        js = ["theme/js/picker.js"]

    def __init__(self, *, source, label="", placeholder="", attrs=None):
        # Stored as a name and resolved on demand: field definitions run at import
        # time, before AppConfig.ready() has populated the registry.
        self.source_name = source
        self.label = label
        self.placeholder = placeholder
        # Set per request by the form so the (perms-less) widget render context can
        # still gate the "open in admin" link on the change_device permission.
        self.user = None
        super().__init__(attrs)

    @property
    def source(self):
        src = get_picker_source(self.source_name)
        if src is None:
            raise ValueError(f"Unknown device picker source: {self.source_name!r}")
        return src

    # Behave like (Multiple)HiddenInput so the bound model field cleans the pk(s).
    def value_from_datadict(self, data, files, name):
        if self.source.multiple:
            return data.getlist(name)
        return data.get(name)

    def value_omitted_from_data(self, data, files, name):
        return name not in data

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        source = self.source

        raw = (value or []) if source.multiple else ([value] if value else [])
        pks = [pk for pk in raw if str(pk).isdigit()]

        queryset = getattr(self.choices, "queryset", None)
        devices = list(queryset.filter(pk__in=pks)) if (queryset is not None and pks) else []

        widget = context["widget"]
        widget.update(
            {
                "picker_id": self.picker_id,
                "source": source.name,
                "multiple": source.multiple,
                "search_param": source.search_param,
                "label": self.label,
                "placeholder": self.placeholder,
                "required": self.is_required,
                # JSON for hx-vals so every live search posts which source to use.
                "hx_vals": json.dumps({"source": source.name}),
                "devices": devices,
                "selected_device": devices[0] if devices else None,
                "has_selected": bool(devices),
                # The widget render context has no `perms` (no context processors),
                # so pass the change_device permission explicitly for the selected
                # cards' "open in admin" link.
                "can_change_device": bool(self.user and self.user.has_perm("core.change_device")),
            }
        )
        return context


class DevicePickerField(forms.ModelChoiceField):
    """Single-select device field rendered by :class:`DevicePickerWidget`."""

    def __init__(self, *, source, queryset, label="", placeholder="", **kwargs):
        super().__init__(
            queryset=queryset,
            widget=DevicePickerWidget(source=source, label=label, placeholder=placeholder),
            **kwargs,
        )


class DevicePickerMultiField(forms.ModelMultipleChoiceField):
    """Multi-select device field rendered by :class:`DevicePickerWidget`."""

    def __init__(self, *, source, queryset, label="", placeholder="", **kwargs):
        super().__init__(
            queryset=queryset,
            widget=DevicePickerWidget(source=source, label=label, placeholder=placeholder),
            **kwargs,
        )
