# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Tests for the record selection logic behind report subscriptions
(notifications.reports.get_affected_records).
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from dlcdb.core.models import Device, DeviceType, InRoomRecord
from dlcdb.notifications.intervals import NotificationInterval
from dlcdb.notifications.models import Subscription
from dlcdb.notifications.reports import FALLBACK_WINDOW_DAYS, get_affected_records


def create_device(edv_id, prefix="ntb", **kwargs):
    device_type, _ = DeviceType.objects.get_or_create(name=prefix.upper(), prefix=prefix)
    return Device.objects.create(device_type=device_type, edv_id=edv_id, **kwargs)


def report_subscription(condition="", event=Subscription.NotificationEventChoices.INROOM, **kwargs):
    # Unsaved instance: get_affected_records only reads attributes.
    defaults = {
        "event": event,
        "condition": condition,
        "interval": NotificationInterval.WEEKLY.value,
    }
    defaults.update(kwargs)
    return Subscription(**defaults)


class GetAffectedRecordsTests(TestCase):
    @property
    def now(self):
        # Evaluated per call: the selection window must end after the records
        # created in the test body.
        return timezone.localtime(timezone.now())

    def test_has_sap_id_excludes_devices_without_sap_id(self):
        InRoomRecord.objects.create(device=create_device("with-sap", sap_id="100"))
        InRoomRecord.objects.create(device=create_device("without-sap"))

        result = get_affected_records(report_subscription(condition=Subscription.ConditionChoices.HAS_SAP_ID), self.now)

        self.assertEqual([record.device.edv_id for record in result.records], ["with-sap"])

    def test_is_pc_matches_device_type_prefix(self):
        InRoomRecord.objects.create(device=create_device("pc1", prefix="pc"))
        InRoomRecord.objects.create(device=create_device("ntb1", prefix="ntb"))

        result = get_affected_records(report_subscription(condition=Subscription.ConditionChoices.IS_PC), self.now)

        self.assertEqual([record.device.edv_id for record in result.records], ["pc1"])

    def test_is_pc_or_notebook_matches_both_prefixes(self):
        InRoomRecord.objects.create(device=create_device("pc1", prefix="pc"))
        InRoomRecord.objects.create(device=create_device("ntb1", prefix="ntb"))
        InRoomRecord.objects.create(device=create_device("srv1", prefix="srv"))

        result = get_affected_records(
            report_subscription(condition=Subscription.ConditionChoices.IS_PC_OR_NOTEBOOK), self.now
        )

        self.assertEqual(
            {record.device.edv_id for record in result.records},
            {"pc1", "ntb1"},
        )

    def test_is_new_pc_or_notebook_requires_identifiers(self):
        complete = create_device("complete", prefix="pc", serial_number="sn-1", mac_address="aa:bb")
        InRoomRecord.objects.create(device=complete)
        InRoomRecord.objects.create(device=create_device("incomplete", prefix="pc", serial_number="", mac_address=""))

        result = get_affected_records(
            report_subscription(condition=Subscription.ConditionChoices.IS_NEW_PC_OR_NOTEBOOK), self.now
        )

        self.assertEqual([record.device.edv_id for record in result.records], ["complete"])

    def test_licence_expires_matches_expired_contracts_only(self):
        expired = create_device("expired", is_licence=True, contract_expiration_date=self.now.date())
        InRoomRecord.objects.create(device=expired)
        running = create_device(
            "running", is_licence=True, contract_expiration_date=self.now.date() + timedelta(days=30)
        )
        InRoomRecord.objects.create(device=running)

        result = get_affected_records(
            report_subscription(condition=Subscription.ConditionChoices.LICENCE_EXPIRES), self.now
        )

        self.assertEqual([record.device.edv_id for record in result.records], ["expired"])

    def test_records_before_last_run_are_excluded(self):
        InRoomRecord.objects.create(device=create_device("older"))

        included = get_affected_records(report_subscription(last_run=self.now - timedelta(hours=1)), self.now)
        excluded = get_affected_records(report_subscription(last_run=self.now + timedelta(minutes=1)), self.now)

        self.assertEqual(included.records.count(), 1)
        self.assertEqual(excluded.records.count(), 0)

    def test_fallback_window_is_used_without_last_run(self):
        subscription = report_subscription(interval=NotificationInterval.YEARLY.value)
        now = self.now

        result = get_affected_records(subscription, now)

        expected_days = FALLBACK_WINDOW_DAYS[NotificationInterval.YEARLY]
        self.assertEqual(result.window_start, now - timedelta(days=expected_days))
