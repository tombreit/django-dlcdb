# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Subscription history records changes made by people, not the scheduler's bookkeeping."""

import datetime
from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from huey.contrib import djhuey

from dlcdb.core.models import Device, InRoomRecord, Person
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Subscription
from dlcdb.notifications.services import create_license_subscriptions
from dlcdb.notifications.tasks import (
    _update_license_subscriptions,
    queue_message,
    queue_messages_for_interval,
    send_message,
)

Events = Subscription.NotificationEventChoices
BOOKKEEPING = {"last_sent", "last_run", "next_scheduled", "modified_at"}


@pytest.fixture
def subscriber(db):
    return Person.objects.create(first_name="Max", last_name="Mustermann", email="max@example.org")


@pytest.fixture
def licence(tenant):
    today = timezone.localdate()
    return Device.objects.create(
        edv_id="lic001",
        is_licence=True,
        tenant=tenant,
        contract_start_date=today - timedelta(days=365),
        contract_expiration_date=today + timedelta(days=90),
    )


@pytest.fixture
def immediate_huey():
    """Run huey tasks inline, like test_report_flows.ImmediateHueyMixin."""
    djhuey.HUEY.immediate = True
    yield
    djhuey.HUEY.immediate = False


def _licence_subscriptions(subscriber, licence):
    """The licence subscriptions as the licence form creates them."""
    expires = timezone.make_aware(datetime.datetime.combine(licence.contract_expiration_date, datetime.time.min))
    results = create_license_subscriptions(
        subscriber,
        licence,
        scheduled_times={Events.CONTRACT_EXPIRES_SOON: expires - timedelta(days=30), Events.CONTRACT_EXPIRED: expires},
    )
    return [result["subscription"] for result in results]


@pytest.mark.django_db
def test_licence_rearm_every_minute_writes_no_history(subscriber, licence):
    _licence_subscriptions(subscriber, licence)
    history_before = Subscription.history.count()

    # The scheduler runs this every minute for 48 hours after a device edit.
    _update_license_subscriptions()
    expires_soon = Subscription.objects.get(event=Events.CONTRACT_EXPIRES_SOON)
    modified_at = expires_soon.modified_at
    assert _update_license_subscriptions() == 0

    expires_soon.refresh_from_db()
    assert expires_soon.modified_at == modified_at  # the second run saved nothing
    expected = timezone.make_aware(datetime.datetime.combine(licence.contract_expiration_date, datetime.time.min))
    assert expires_soon.next_scheduled == expected - timedelta(days=30)
    assert Subscription.history.count() == history_before


@pytest.mark.django_db
def test_changed_contract_date_reschedules_without_history(subscriber, licence):
    _licence_subscriptions(subscriber, licence)
    _update_license_subscriptions()
    history_before = Subscription.history.count()

    licence.contract_expiration_date += timedelta(days=60)
    licence.save()

    assert _update_license_subscriptions() == 2
    expired = Subscription.objects.get(event=Events.CONTRACT_EXPIRED)
    assert timezone.localtime(expired.next_scheduled).date() == licence.contract_expiration_date
    assert Subscription.history.count() == history_before


@pytest.mark.django_db
def test_queueing_and_sending_write_no_history(subscriber, licence):
    subscription = Subscription.objects.create(
        event=Events.CONTRACT_EXPIRED,
        subscriber=subscriber,
        device=licence,
        interval=NotificationInterval.POINT_IN_TIME.value,
        next_scheduled=timezone.now() - timedelta(minutes=5),
    )
    history_before = Subscription.history.count()

    send_message.call_local(queue_message.call_local(subscription.id))

    subscription.refresh_from_db()
    assert subscription.last_sent is not None
    assert Subscription.history.count() == history_before


@pytest.mark.django_db
def test_report_run_writes_no_history(immediate_huey, media_root):
    InRoomRecord.objects.create(device=Device.objects.create(edv_id="ntb001", sap_id="4711"))
    subscription = Subscription.objects.create(
        subscriber=Person.objects.create(first_name="IT", last_name="Support", email="it@example.org"),
        event=Events.INROOM,
        condition=Subscription.ConditionChoices.HAS_SAP_ID,
        interval=NotificationInterval.DAILY.value,
        next_scheduled=timezone.now() - timedelta(minutes=5),
    )
    history_before = Subscription.history.count()

    queue_messages_for_interval.call_local(NotificationInterval.DAILY)

    subscription.refresh_from_db()
    assert subscription.last_run is not None
    assert subscription.next_scheduled > timezone.now()
    assert Subscription.history.count() == history_before


@pytest.mark.django_db
def test_creating_licence_subscriptions_writes_one_row_each(subscriber, licence):
    subscriptions = _licence_subscriptions(subscriber, licence)

    assert Subscription.history.count() == len(subscriptions)
    assert set(Subscription.history.values_list("history_type", flat=True)) == {"+"}


@pytest.mark.django_db
def test_changes_by_people_keep_their_history(subscriber, licence):
    [subscription, *_] = _licence_subscriptions(subscriber, licence)

    subscription.is_active = False
    subscription.save()

    latest = subscription.history.latest()
    assert latest.history_type == "~"
    assert latest.is_active is False


def test_history_does_not_track_scheduler_bookkeeping():
    tracked = {field.name for field in Subscription.history.model._meta.get_fields()}
    assert not tracked & BOOKKEEPING


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_cleanup_migration_keeps_only_real_changes():
    old_apps = _migrate([("notifications", "0004_copy_mail_log_to_journal")])
    OldHistory = old_apps.get_model("notifications", "HistoricalSubscription")
    start = timezone.now() - timedelta(days=30)

    def row(subscription_id, minute, history_type="~", is_active=True, reason=None):
        return OldHistory.objects.create(
            id=subscription_id,
            event="CONTRACT_EXPIRED",
            interval="point_in_time",
            subscriber_id=1,
            device_id=1,
            subscribed_at=start,
            created_at=start,
            modified_at=start + timedelta(minutes=minute),
            is_active=is_active,
            notify_no_updates=False,
            next_scheduled=start + timedelta(days=60),
            history_date=start + timedelta(minutes=minute),
            history_type=history_type,
            history_change_reason=reason,
        )

    created = row(1, 0, "+")
    for minute in range(1, 6):
        row(1, minute)  # the scheduler's per-minute saves
    deactivated = row(1, 6, is_active=False)
    for minute in range(7, 10):
        row(1, minute, is_active=False)
    explained = row(1, 10, is_active=False, reason="Subscriber removed by an admin")
    deleted = row(1, 11, "-", is_active=False)
    other_created = row(2, 0, "+")
    row(2, 1)
    row(2, 2)

    new_apps = _migrate([("notifications", "0005_drop_repeated_subscription_history")])
    NewHistory = new_apps.get_model("notifications", "HistoricalSubscription")

    assert set(NewHistory.objects.values_list("history_id", flat=True)) == {
        created.history_id,
        deactivated.history_id,
        explained.history_id,
        deleted.history_id,
        other_created.history_id,
    }

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
