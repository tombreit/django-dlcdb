# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Helpers to inspect a rendered form page the way a browser sees it.

A ModelForm can only preserve what the *page* carries: a field that is not
rendered is not submitted, and Django writes the resulting empty value back over
the stored one. These helpers therefore read the HTML, not the form object -- see
``test_form_round_trip`` for the invariants built on them.
"""

import re


# Django renders every attribute double-quoted, so a plain attribute scan is
# enough here and keeps the helpers dependency-free.
_TAG_RE = re.compile(r"<(?:input|select|textarea)\b[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r'([\w:-]+)="([^"]*)"')

ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _tag_attrs(html):
    """Every form control in ``html`` as an attribute dict."""
    return [dict(_ATTR_RE.findall(tag)) for tag in _TAG_RE.findall(html)]


def rendered_input_names(html):
    """The names a browser would submit from this page."""
    return {attrs["name"] for attrs in _tag_attrs(html) if attrs.get("name")}


def date_input_values(html):
    """``(name, value)`` for every ``<input type="date">`` on the page.

    An ``<input type="date">`` displays and submits ISO only. Any other notation
    is shown as an empty field and posted back empty, which wipes the stored date.
    """
    return [
        (attrs.get("name", ""), attrs.get("value", ""))
        for attrs in _tag_attrs(html)
        if attrs.get("type", "").lower() == "date"
    ]
