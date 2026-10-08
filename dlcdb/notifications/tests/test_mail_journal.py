# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""Notification mails in the journal: one entry per sent mail and per newly failed one."""

from datetime import timedelta
from smtplib import SMTPException

import pytest
from django.core import mail
from django.core.mail import EmailMessage
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from dlcdb.core.models import Device, Person
from dlcdb.journal.models import JournalEntry
from dlcdb.notifications.channels import EmailChannel
from dlcdb.notifications.models import Message, Subscription

Level = JournalEntry.Level


@pytest.fixture
def licence(tenant):
    return Device.objects.create(edv_id="lic001", is_licence=True, tenant=tenant)


def _message(device, *, email="max@example.org", **kwargs):
    subscriber = Person.objects.create(first_name="Max", last_name="Mustermann", email=email)
    subscription = Subscription.objects.create(
        event=Subscription.NotificationEventChoices.CONTRACT_EXPIRED, subscriber=subscriber, device=device
    )
    return Message.objects.create(subscription=subscription, subject="License expired", body="Body", **kwargs)


@pytest.fixture
def smtp_down(monkeypatch):
    def fail(self):
        raise SMTPException("SMTP down")

    monkeypatch.setattr(EmailMessage, "send", fail)


@pytest.mark.django_db
def test_sent_mail_adds_one_entry(licence, tenant):
    message = _message(licence, cc_email="it@example.org")

    assert EmailChannel.send(message) is True

    assert len(mail.outbox) == 1
    entry = JournalEntry.objects.get()
    assert entry.source == "notifications.mail"
    assert entry.event == "sent"
    assert entry.level == Level.SUCCESS
    assert entry.summary == "Mail sent: License expired"
    assert entry.body == "To: max@example.org\nCc: it@example.org"
    assert entry.user is None
    assert entry.tenant == tenant
    assert entry.content_object == message


@pytest.mark.django_db
def test_failed_mail_is_journaled_once_until_it_is_sent(licence, monkeypatch, smtp_down):
    message = _message(licence)

    assert EmailChannel.send(message) is False
    assert EmailChannel.send(Message.objects.get(pk=message.pk)) is False  # the retry fails again

    failed = JournalEntry.objects.get()
    assert failed.event == "failed"
    assert failed.level == Level.ERROR
    assert failed.summary == "Mail failed: License expired"
    assert failed.body == "SMTP down"
    # The channel's own log line is not journaled a second time.
    assert not JournalEntry.objects.filter(event__in=["log", "exception"]).exists()

    monkeypatch.undo()
    assert EmailChannel.send(Message.objects.get(pk=message.pk)) is True
    assert list(JournalEntry.objects.order_by("pk").values_list("event", flat=True)) == ["failed", "sent"]


@pytest.mark.django_db
def test_mail_without_recipient_is_journaled_as_failed(licence):
    message = _message(licence, email="")

    assert EmailChannel.send(message) is False

    entry = JournalEntry.objects.get()
    assert entry.event == "failed"
    assert entry.body == "No recipient email address"


@pytest.mark.django_db
def test_standalone_mail_has_no_tenant():
    message = Message.objects.create(recipient_email="lender@example.org", subject="Overdue lending", body="Body")

    EmailChannel.send(message)

    entry = JournalEntry.objects.get()
    assert entry.tenant is None
    assert entry.body == "To: lender@example.org"


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    executor.loader.build_graph()
    return executor._create_project_state(with_applied_migrations=True).apps


@pytest.mark.django_db(transaction=True)
def test_copy_migration_journals_sent_and_failed_mails():
    old_apps = _migrate([("notifications", "0003_message_cc_email"), ("journal", "0001_initial")])
    Tenant = old_apps.get_model("tenants", "Tenant")
    OldDevice = old_apps.get_model("core", "Device")
    OldPerson = old_apps.get_model("core", "Person")
    OldSubscription = old_apps.get_model("notifications", "Subscription")
    OldMessage = old_apps.get_model("notifications", "Message")

    tenant = Tenant.objects.create(name="MigTenant")
    device = OldDevice.objects.create(edv_id="lic-mig", is_licence=True, tenant=tenant, username="")
    subscriber = OldPerson.objects.create(
        first_name="Ada", last_name="Lovelace", email="ada@example.org", udb_person_email_internal_business=""
    )
    subscription = OldSubscription.objects.create(event="contract_expired", subscriber=subscriber, device=device)
    sent_at = timezone.now() - timedelta(days=3)
    sent = OldMessage.objects.create(
        subscription=subscription, status="sent", subject="License expired", sent_at=sent_at, cc_email="it@x.org"
    )
    failed = OldMessage.objects.create(
        recipient_email="lender@example.org", status="failed", subject="Overdue", error_message="SMTP down"
    )
    OldMessage.objects.create(recipient_email="later@example.org", status="pending")

    new_apps = _migrate([("notifications", "0004_copy_mail_log_to_journal")])
    NewJournalEntry = new_apps.get_model("journal", "JournalEntry")

    entries = {entry.object_id: entry for entry in NewJournalEntry.objects.filter(source="notifications.mail")}
    assert set(entries) == {sent.pk, failed.pk}
    sent_entry, failed_entry = entries[sent.pk], entries[failed.pk]
    assert (sent_entry.event, sent_entry.level, sent_entry.summary) == (
        "sent",
        Level.SUCCESS,
        "Mail sent: License expired",
    )
    assert sent_entry.body == "To: ada@example.org\nCc: it@x.org"
    assert sent_entry.timestamp == sent_at
    assert sent_entry.tenant_id == tenant.pk
    assert sent_entry.object_repr == f"{sent.pk} - sent - subscription {subscription.pk}"
    assert (failed_entry.event, failed_entry.level, failed_entry.body) == ("failed", Level.ERROR, "SMTP down")
    assert failed_entry.tenant_id is None
    assert failed_entry.object_repr == f"{failed.pk} - failed - lender@example.org"

    # Leave the schema at head so the test DB stays consistent for other tests.
    _migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
