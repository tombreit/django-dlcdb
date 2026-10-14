# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""The attachment admin lists the records an attachment belongs to, with their date."""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from dlcdb.core.models import Attachment, InRoomRecord, Room
from dlcdb.core.tests.basetest import BaseTest

_PLAIN_STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_PLAIN_STATIC_STORAGE)
class AttachmentAdminTests(BaseTest):
    def setUp(self):
        user = get_user_model().objects.create_superuser(email="admin@example.org", password="secret")
        self._join_default_tenant(user)
        self.client.force_login(user)
        # A file name only: the admin links to it but never reads it.
        self.attachment = Attachment.objects.create(title="Disposal certificate", file="attachments/disposal.pdf")
        record = InRoomRecord.objects.create(device=self._create_device(), room=Room.objects.create(number="A1.01"))
        record.attachments.add(self.attachment)
        # get_records renders one link per record; on an error the admin shows "-"
        # in the change page's read-only field instead.
        record_url = reverse("admin:core_record_change", args=[record.pk])
        self.record_link = f"<a href='{record_url}'>{record} / {record.record_type} / "
        self.record_date = timezone.localdate(record.created_at).isoformat()

    def test_the_list_shows_the_records_of_an_attachment(self):
        response = self.client.get(reverse("admin:core_attachment_changelist"))

        self.assertContains(response, f"{self.record_link}{self.record_date}</a>")

    def test_the_change_page_shows_the_records_of_an_attachment(self):
        response = self.client.get(reverse("admin:core_attachment_change", args=[self.attachment.pk]))

        self.assertContains(response, f"{self.record_link}{self.record_date}</a>")
