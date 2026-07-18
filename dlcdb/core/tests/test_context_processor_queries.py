# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The context processors run on every frontend page render, so they must not
issue redundant queries: one aggregate for the room hints, one for the
record-less device hint, and at most one (request-memoized) active-inventory
lookup shared by nav() and the inventory context processor.
See https://adamj.eu/tech/2023/03/23/django-context-processors-database-queries/
"""

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from dlcdb.core.context_processors import hints, nav
from dlcdb.core.models import Inventory, Room
from dlcdb.core.models.inventory import get_active_inventory
from dlcdb.core.tests.basetest import BaseTest


class ContextProcessorQueryTests(BaseTest):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(email="admin@example.com", password="secret")
        cls.plain_user = get_user_model().objects.create_user(
            email="user@example.com", password="secret", username="plain-user"
        )
        cls.inventory = Inventory.objects.create(name="2026", is_active=True)
        Room.objects.create(number="F1.01")

    def _request(self, user):
        request = RequestFactory().get("/")
        request.user = user
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        return request

    def _table_queries(self, captured, table):
        return [query["sql"] for query in captured.captured_queries if table in query["sql"]]

    def test_hints_issues_one_room_and_one_device_query(self):
        device = self._create_device(edv_id="EDV-NO-RECORD", sap_id="1-1")
        request = self._request(self.superuser)

        with CaptureQueriesContext(connection) as captured:
            hints(request)

        self.assertEqual(len(self._table_queries(captured, "core_room")), 1)
        self.assertEqual(len(self._table_queries(captured, "core_device")), 1)

        # The single record-less device is still linked directly, without the
        # former extra .first() query.
        stored_messages = [str(message) for message in request._messages]
        self.assertTrue(any(f"?device={device.pk}" in message for message in stored_messages))

    def test_nav_memoizes_active_inventory_query(self):
        # Three nav entries carry show_condition "active_inventory_exists"
        # (dlcdb/inventory/navigation.py), but the lookup must run only once.
        request = self._request(self.superuser)

        with CaptureQueriesContext(connection) as captured:
            nav(request)

        self.assertEqual(len(self._table_queries(captured, "core_inventory")), 1)

    def test_nav_skips_inventory_query_without_permission(self):
        request = self._request(self.plain_user)

        with CaptureQueriesContext(connection) as captured:
            nav(request)

        self.assertEqual(len(self._table_queries(captured, "core_inventory")), 0)

    def test_get_active_inventory_is_memoized_per_request(self):
        request = self._request(self.superuser)

        with CaptureQueriesContext(connection) as captured:
            first = get_active_inventory(request)
            second = get_active_inventory(request)

        self.assertEqual(len(captured.captured_queries), 1)
        self.assertEqual(first, self.inventory)
        self.assertIs(first, second)

        # A new request gets a fresh lookup.
        with CaptureQueriesContext(connection) as captured:
            get_active_inventory(self._request(self.superuser))

        self.assertEqual(len(captured.captured_queries), 1)
