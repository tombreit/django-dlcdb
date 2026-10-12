# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The "contract expires soon" notice is scheduled twice: by the licence form when a
subscriber is added, and by the scheduler after the licence is edited. Both must
arrive at the same date.
"""

import datetime
from datetime import timedelta

import pytest
from django.utils import timezone

from dlcdb.core.models import Device, Person
from dlcdb.licenses.subscribers import manage_subscribers
from dlcdb.notifications.models import Subscription
from dlcdb.notifications.tasks import _update_license_subscriptions


@pytest.mark.django_db
def test_form_and_scheduler_schedule_the_expires_soon_notice_alike(tenant):
    expires = datetime.date(2027, 3, 31)
    licence = Device.objects.create(edv_id="lic001", is_licence=True, tenant=tenant, contract_expiration_date=expires)
    Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")

    manage_subscribers(licence, Person.objects.all())

    expires_soon = Subscription.objects.get(event=Subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON)
    due = timezone.make_aware(datetime.datetime.combine(expires, datetime.time.min)) - timedelta(
        days=Subscription.CONTRACT_EXPIRES_SOON_DAYS
    )
    assert expires_soon.next_scheduled == due
    # The licence was just saved, so the scheduler recomputes its dates and finds
    # nothing to change.
    assert _update_license_subscriptions() == 0
