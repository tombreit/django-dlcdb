# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Queueing messages per interval, with huey storing no task results."""

from datetime import timedelta

import pytest
from django.utils import timezone
from huey.contrib import djhuey

from dlcdb.core.models import Device, InRoomRecord, Person
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Message, Subscription
from dlcdb.notifications.tasks import queue_messages_for_interval

Events = Subscription.NotificationEventChoices


def test_huey_stores_no_task_results():
    # Stored results never expire in the SQLite backend and nothing reads them:
    # they grew the production queue file to 7 GB.
    assert djhuey.HUEY.results is False


@pytest.fixture
def immediate_huey():
    """Run huey tasks inline, like test_report_flows.ImmediateHueyMixin."""
    djhuey.HUEY.immediate = True
    yield
    djhuey.HUEY.immediate = False


@pytest.mark.django_db
def test_interval_run_returns_the_report_messages_it_created(immediate_huey, media_root):
    subscriber = Person.objects.create(first_name="IT", last_name="Support", email="it@example.org")
    device = Device.objects.create(edv_id="ntb001", sap_id="4711")
    InRoomRecord.objects.create(device=device)
    Subscription.objects.create(
        subscriber=subscriber,
        event=Events.INROOM,
        condition=Subscription.ConditionChoices.HAS_SAP_ID,
        interval=NotificationInterval.DAILY.value,
        next_scheduled=timezone.now() - timedelta(minutes=5),
    )
    moved = Subscription.objects.create(
        subscriber=subscriber,
        event=Events.MOVED,
        device=device,
        interval=NotificationInterval.DAILY.value,
        next_scheduled=timezone.now() - timedelta(minutes=5),
    )

    created = queue_messages_for_interval.call_local(NotificationInterval.DAILY)

    assert created == 1  # the report; the queued check for `moved` is counted separately
    assert Message.objects.filter(report__isnull=False).count() == 1
    assert Message.objects.filter(subscription=moved).exists()
