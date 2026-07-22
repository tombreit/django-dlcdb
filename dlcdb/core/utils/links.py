# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Turning the objects named in a Django message into links to their detail views.

A transition message like "Device “SON60000895” moved to room “235”." is more
useful when the device and the room are clickable. ``linked_message`` does the
``%``-substitution for such a message, running every value through ``obj_link``,
so the message text (the translatable msgid) stays exactly as it was.

Putting HTML into a Django message is an established pattern in this project:
``dlcdb.core.context_processors.StickyMessage.get_formatted_msg`` already does
it, and both message renderers (``theme/_base.html`` and the django-admin
default) pass a ``SafeString`` through untouched.
"""

from django.urls import NoReverseMatch, reverse
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString


def obj_link(obj, label=None) -> SafeString:
    """
    Render ``obj`` as a link to its frontend detail view.

    Linkable are ``Device`` (licences go to their licence form, everything else
    to the device detail), ``Room`` and ``Person``. Anything else — a plain
    string, a tenant, ``None`` — is returned as escaped text, so callers can pass
    every part of a message through here without checking its type first.

    ``label`` overrides the anchor text, which would otherwise be ``str(obj)``.
    """
    # Imported here (not at module level) to keep core.utils importable without
    # pulling in core.models, which imports from core.utils itself.
    from ..models import Device, Person, Room

    url = None
    try:
        if isinstance(obj, Device):
            # Licences have their own edit form; get_absolute_url() knows about
            # it and returns None for regular devices.
            url = obj.get_absolute_url() or reverse("assets:device_detail", args=[obj.pk])
        elif isinstance(obj, Room):
            url = reverse("rooms:detail", args=[obj.pk])
        elif isinstance(obj, Person):
            url = reverse("persons:detail", args=[obj.pk])
    except NoReverseMatch:
        url = None

    text = obj if label is None else label
    if url is None or getattr(obj, "pk", None) is None:
        # conditional_escape, not escape: an already-safe value (a pre-built
        # anchor from a caller that needed a custom label) passes through.
        return conditional_escape(text)

    return format_html('<a href="{}">{}</a>', url, text)


def linked_message(template, **parts) -> SafeString:
    """
    ``template.format(**parts)`` with every part rendered via ``obj_link``.

    ``template`` is a (usually translated) message with named ``{…}``
    placeholders, e.g. ``_("Device “{device}” moved to room “{room}”.")``. Note
    that it is a ``str.format`` template, so a literal brace in a message has to
    be doubled — none of ours contain one, they use curly quotes.

    Note that an f-string cannot replace the placeholders here: it would
    interpolate before ``gettext`` sees the string, so the message would no
    longer be translatable.

    Escaping is ``format_html``'s job: it runs every argument through
    ``conditional_escape`` (a no-op for the anchors ``obj_link`` built, escaping
    for everything else) and marks only the result safe.
    """
    return format_html(str(template), **{key: obj_link(value) for key, value in parts.items()})
