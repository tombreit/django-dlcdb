# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms

from dlcdb.theme.forms import add_bootstrap_classes


class _IdentifierForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={"class": "font-monospace"}))
    name = forms.CharField()
    kind = forms.ChoiceField(choices=[("a", "A")])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


def _class(form, name):
    return form.fields[name].widget.attrs["class"]


def test_a_class_the_form_declares_stays_after_bootstraps():
    form = _IdentifierForm()

    assert _class(form, "code") == "form-control font-monospace"
    assert _class(form, "name") == "form-control"
    assert _class(form, "kind") == "form-select"


def test_the_declared_class_does_not_pile_up_across_form_instances():
    _IdentifierForm()

    assert _class(_IdentifierForm(), "code") == "form-control font-monospace"


def test_an_invalid_field_keeps_the_declared_class():
    form = _IdentifierForm(data={"code": "", "name": "x", "kind": "a"})

    assert _class(form, "code") == "form-control font-monospace is-invalid"
