# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
System-level reminder mails to lenders whose lendings are overdue.
Not backed by subscriptions: who is overdue is derived state, recalculated
on every run.
"""

import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Message
from .reports import get_lent_overdue_records

logger = logging.getLogger(__name__)


def create_overdue_lender_messages(*, now=None) -> list[Message]:
    """
    Create one standalone pending Message per person with overdue lendings,
    listing all their overdue devices. Sending is left to the caller.
    """
    now = now or timezone.localtime(timezone.now())
    overdue_records = get_lent_overdue_records(now)

    messages = []
    for lender_pk in set(overdue_records.values_list("person__pk", flat=True)):
        records = list(overdue_records.filter(person__pk=lender_pk))
        person = records[0].person

        # In a testdrive, mails go to the IT department instead of the lenders.
        recipient = (
            settings.DEFAULT_FROM_EMAIL if settings.NOTIFICATIONS_NOTIFY_OVERDUE_LENDERS_TO_IT else person.get_email
        )

        if not recipient:
            logger.warning(f"Skipping overdue lender mail for {person} (pk={person.pk}): no email address")
            continue

        context = {
            "person": person,
            "records": records,
            "records_count": len(records),
            "contact_email": settings.DEFAULT_FROM_EMAIL,
        }
        message = Message.objects.create(
            recipient_email=recipient,
            subject=render_to_string("notifications/emails/overdue_lenders_subject.txt", context).strip(),
            body=render_to_string("notifications/emails/overdue_lenders_body.txt", context),
        )
        messages.append(message)

    logger.info(f"Created {len(messages)} overdue lender messages")
    return messages
