# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from django.utils import timezone


def spreadsheet_directory_path(instance, filename):
    return "reporting/spreadsheets/{0}".format(filename)


class Report(models.Model):
    """
    A generated report artifact: title, text rows and an xlsx spreadsheet.
    Created via services.create_report(); notification/delivery concerns
    live in the dlcdb.notifications app.
    """

    title = models.CharField(
        max_length=255,
        blank=True,
    )
    body = models.TextField(
        blank=True,
    )
    spreadsheet = models.FileField(
        blank=True,
        upload_to=spreadsheet_directory_path,
        editable=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt",
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Geändert",
    )

    def __str__(self):
        return "{0}: {1} {2}".format(
            self.pk,
            timezone.localtime(self.created_at),
            self.title,
        )

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
