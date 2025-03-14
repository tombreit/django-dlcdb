# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models


class RemoverList(models.Model):
    VALID_COL_HEADERS = [
        "SAP_ID",
        "EDV_ID",
        "NOTE",
        "DISPOSITION_STATE",
        "REMOVED_INFO",
        "REMOVED_DATE",
        "USERNAME",
    ]

    file = models.FileField(
        upload_to="toremove_csv",
        verbose_name="CSV-Datei",
        help_text="Valide Spaltenköpfe: <br>{}".format("<br>".join(VALID_COL_HEADERS)),
    )
    note = models.TextField(
        blank=True,
        verbose_name="Anmerkung",
    )
    messages = models.TextField(
        blank=True,
        verbose_name="DLCDB-Ausgaben zu diesem Vorgang",
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

    class Meta:
        verbose_name = "Ausmusterungs-Datei"
        verbose_name_plural = "Ausmusterungs-Dateien"
        ordering = ["-modified_at", "-created_at"]

    def __str__(self):
        return "{}".format(self.file)
