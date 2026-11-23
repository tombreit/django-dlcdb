# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Turning the objects named in a Django message into links to their detail views.

A transition message like "Device “SON60000895” moved to room “235”." is more
useful when the device and the room are clickable. ``linked_message`` fills the
``{…}`` placeholders of such a message (``str.format``), running every value
through ``obj_link``.

Putting HTML into a Django message is an established pattern in this project:
``StickyMessage.get_formatted_msg`` in ``dlcdb.theme.context_processors.hints``
already does it, and both message renderers (``theme/_base.html`` and the
django-admin default) pass a ``SafeString`` through untouched.
"""

from django.urls import NoReverseMatch, reverse
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import SafeString

# The pages of the models without get_absolute_url, by ``_meta.label_lower``.
# URL names, not imports: core imports no other app.
DETAIL_URLS = {
    "core.room": "rooms:detail",
    "core.person": "persons:detail",
    "core.devicetype": "assets:device_type:edit",
    "core.manufacturer": "assets:manufacturer:edit",
    "core.supplier": "assets:supplier:edit",
    "core.organizationalunit": "organization:unit:edit",
    "core.organizationalposition": "organization:position:edit",
    "tenants.tenant": "tenants:detail",
    "lending.lendingprofile": "lending:profile:edit",
    "core.link": "lending:regulation:edit",
    "smallstuff.thing": "smallstuff:thing:edit",
    "auth.group": "accounts:group_detail",
}


def detail_url(obj):
    """
    The frontend page of ``obj``: its ``get_absolute_url()`` (a device, a
    licence, an import), else its entry in ``DETAIL_URLS``.

    None for anything without a page: a plain value, an unsaved object, a
    soft-deleted one (its page answers 404).
    """
    if getattr(obj, "pk", None) is None or getattr(obj, "deleted_at", None):
        return None
    try:
        if hasattr(obj, "get_absolute_url"):
            return obj.get_absolute_url()
        url_name = DETAIL_URLS.get(obj._meta.label_lower)
        return reverse(url_name, args=[obj.pk]) if url_name else None
    except NoReverseMatch:
        return None


def obj_link(obj, label=None) -> SafeString:
    """
    Render ``obj`` as a link to its frontend page (``detail_url``).

    Anything without a page — a plain string, ``None``, a soft-deleted room — is
    returned as escaped text, so callers can pass every part of a message
    through here without checking its type first.

    ``label`` overrides the anchor text, which would otherwise be ``str(obj)``.
    """
    url = detail_url(obj)
    text = obj if label is None else label
    if url is None:
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
