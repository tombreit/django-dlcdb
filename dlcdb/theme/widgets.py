# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json

from django import forms

from .bootstrap_icons import get_bootstrap_icons


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
