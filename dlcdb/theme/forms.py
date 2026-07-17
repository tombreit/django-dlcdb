# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Form styling helpers shared by the frontend apps.

Pure functions called from a form's ``__init__`` — the project deliberately has
no form mixins or custom template tags.
"""

from django import forms

from .widgets import TomSelectMultipleWidget, TomSelectWidget


def add_bootstrap_classes(form):
    """
    Apply the Bootstrap 5 control classes to every widget of ``form``, and mark
    bound fields that failed validation with ``.is-invalid`` so they render in
    the invalid state (red border + icon). The messages themselves are emitted
    as ``.invalid-feedback`` next to each control in the template.
    https://getbootstrap.com/docs/5.3/forms/validation/

    Hidden (picker-driven) fields and TomSelect widgets are left alone: the
    former carry no visible control, the latter already ship their own classes.
    """
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.HiddenInput):
            continue
        if isinstance(widget, (TomSelectWidget, TomSelectMultipleWidget)):
            continue
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs["class"] = "form-check-input"
        elif isinstance(widget, forms.Select):
            widget.attrs["class"] = "form-select"
        else:
            widget.attrs["class"] = "form-control"

    if form.is_bound:
        for name in form.errors:
            field = form.fields.get(name)
            if field is None or isinstance(field.widget, forms.HiddenInput):
                continue  # non-field ("__all__") or picker-driven field
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} is-invalid".strip()
