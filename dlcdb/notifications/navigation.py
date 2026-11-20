# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.utils.translation import gettext_lazy as _

nav_entries = [
    {
        "slot": "nav_settings",
        "order": 50,
        "label": _("Notification messages"),
        "group": "modules",
        "description": _("Pending, sent and failed mails, with preview and Send now"),
        "search_terms": _("mails, email, outbox, queue, errors, subscriptions"),
        "icon": "bi bi-envelope",
        "url": "admin:notifications_message_changelist",
        "required_permission": "notifications.view_message",
    },
]
