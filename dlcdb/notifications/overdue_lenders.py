# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
System-level reminder mails to lenders whose lendings are overdue.
Not backed by subscriptions: who is overdue is derived state, recalculated
on every run.
"""

import logging

from django.template.loader import render_to_string
from django.utils import timezone

from dlcdb.core.utils.helpers import get_contact_email
from dlcdb.lending.models import LendingConfiguration

from .email_footer import email_footer_context
from .models import Message
from .reports import get_lent_overdue_records

logger = logging.getLogger(__name__)


def create_overdue_lender_messages(*, now=None) -> list[Message]:
    """
    Create one standalone pending Message per (person, tenant) with overdue
    lendings, listing that tenant's overdue devices. Splitting per tenant lets
    each mail's IT copy go to the tenant responsible for those devices (via
    device.tenant). Sending is left to the caller.
    """
    now = now or timezone.localtime(timezone.now())
    overdue_records = get_lent_overdue_records(now)

    Recipient = LendingConfiguration.OverdueNotificationRecipient
    mode = LendingConfiguration.load().overdue_notifications_recipient
    if mode == Recipient.NONE:
        return []

    messages = []
    groups = set(overdue_records.values_list("person__pk", "device__tenant"))
    for lender_pk, tenant_pk in groups:
        records = list(overdue_records.filter(person__pk=lender_pk, device__tenant=tenant_pk))
        person = records[0].person
        tenant = records[0].device.tenant
        it_email = get_contact_email(tenant)

        if mode == Recipient.IT:
            # Testdrive: the lender's mail is rerouted to IT, no lender copy.
            recipient, cc = it_email, ""
        else:  # LENDER or LENDER_AND_IT
            recipient = person.get_email
            cc = it_email if mode == Recipient.LENDER_AND_IT else ""

        if not recipient:
            logger.warning(f"Skipping overdue lender mail for {person} (pk={person.pk}): no email address")
            continue

        context = {
            "person": person,
            "records": records,
            "records_count": len(records),
            **email_footer_context(tenant=tenant),
        }
        message = Message.objects.create(
            recipient_email=recipient,
            cc_email=cc,
            subject=render_to_string("notifications/emails/overdue_lenders_subject.txt", context).strip(),
            body=render_to_string("notifications/emails/overdue_lenders_body.txt", context),
        )
        messages.append(message)

    logger.info(f"Created {len(messages)} overdue lender messages")
    return messages
