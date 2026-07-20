# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The shared contact-email resolver (core.utils.helpers.get_contact_email)
resolves through the chain: tenant.contact_email -> Branding IT dept email ->
settings.DEFAULT_FROM_EMAIL.
"""

from django.conf import settings
from django.test import TestCase

from dlcdb.core.utils.helpers import get_contact_email
from dlcdb.organization.models import Branding
from dlcdb.tenants.models import Tenant


class GetContactEmailTests(TestCase):
    def test_tenant_contact_email_wins(self):
        branding = Branding.load()
        branding.organization_it_dept_email = "it-dept@example.org"
        branding.save()
        tenant = Tenant.objects.create(name="Tenant A", contact_email="it-a@example.org")

        self.assertEqual(get_contact_email(tenant), "it-a@example.org")

    def test_falls_back_to_branding_when_tenant_has_no_email(self):
        branding = Branding.load()
        branding.organization_it_dept_email = "it-dept@example.org"
        branding.save()
        tenant = Tenant.objects.create(name="Tenant B")

        self.assertEqual(get_contact_email(tenant), "it-dept@example.org")

    def test_falls_back_to_branding_when_no_tenant_given(self):
        branding = Branding.load()
        branding.organization_it_dept_email = "it-dept@example.org"
        branding.save()

        self.assertEqual(get_contact_email(), "it-dept@example.org")

    def test_last_resort_is_default_from_email(self):
        # Neither a tenant address nor a Branding IT dept email configured.
        self.assertEqual(get_contact_email(), settings.DEFAULT_FROM_EMAIL)
