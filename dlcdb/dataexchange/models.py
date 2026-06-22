# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..core.models.abstracts import SingletonBaseModel


class ImporterList(models.Model):
    VALID_COL_HEADERS = [
        "SAP_ID",
        "ROOM",
        "EDV_ID",
        "DEVICE_TYPE",
        "SERIAL_NUMBER",
        "MANUFACTURER",
        "SERIES",
        "SUPPLIER",
        "PURCHASE_DATE",
        "WARRANTY_EXPIRATION_DATE",
        "CONTRACT_EXPIRATION_DATE",
        "COST_CENTRE",
        "BOOK_VALUE",
        "NOTE",
        "MAC_ADDRESS",
        "EXTRA_MAC_ADDRESSES",
        "NICK_NAME",
        "IS_LENTABLE",
        "IS_LICENCE",
        "RECORD_TYPE",
        "RECORD_NOTE",
        "REMOVED_DATE",
        "ORDER_NUMBER",
        # LENT record columns:
        "LENDER_FIRST_NAME",
        "LENDER_LAST_NAME",
        "LENDER_EMAIL",
        "LENDER_OU",
        "LENT_START_DATE",
        "LENT_DESIRED_END_DATE",
        "LENT_END_DATE",
        "LENT_NOTE",
        "LENT_REASON",
        "LENT_ACCESSORIES",
    ]

    class ImportFormatChoices(models.TextChoices):
        INTERNALCSV = "INTCSV", _("Internal (CSV)")
        SAPCSV = "SAPCSV", _("SAP (CSV)")

    file = models.FileField(
        upload_to="imported_csv",
        verbose_name="CSV-Datei",
        help_text="Valide Spaltenköpfe: <br>{}".format("<br>".join(VALID_COL_HEADERS)),
    )
    note = models.TextField(
        null=True,
        blank=True,
        verbose_name="Anmerkung",
    )
    import_format = models.CharField(
        max_length=10,
        choices=ImportFormatChoices.choices,
        default=ImportFormatChoices.INTERNALCSV,
        help_text=f"Specifiy the format of the import file. Currently officially supported is only '{ImportFormatChoices.INTERNALCSV},'.",
    )
    tenant = models.ForeignKey(
        "tenants.tenant", null=True, on_delete=models.SET_NULL, help_text="Import as given tenant."
    )
    messages = models.TextField(
        blank=True,
        verbose_name="DLCDB-Ausgaben zu diesem Import",
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
        verbose_name = "Import-Datei"
        verbose_name_plural = "Import-Dateien"
        ordering = ["-modified_at", "-created_at"]

    def __str__(self):
        return "{}".format(self.file)


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


class UdbSyncConfiguration(SingletonBaseModel):
    """
    Admin-managed configuration for the periodic UDB person sync.

    Operators own the source URL and the API token here (no redeploy needed).
    The request *filters* and *fields* (``contract-fields`` / ``person-fields``)
    are intentionally NOT configurable: they are stable business rules and the
    sync code reads a fixed set of keys, so both live in code (see
    ``udb_sync.UDB_SYNC_FILTERS`` / ``UDB_SYNC_CONTRACT_FIELDS`` / ``UDB_SYNC_PERSON_FIELDS``). ``clean()``
    keeps the admin-owned ``url`` from colliding with that code-owned query.
    """

    enabled = models.BooleanField(
        default=False,
        help_text="If unchecked, the periodic sync and the management command exit immediately.",
    )
    url = models.URLField(
        blank=True,
        verbose_name="UDB URL",
        help_text=(
            "Complete URL of the UDB contracts API endpoint or a ready-made JSON dump, "
            "without a query string — e.g. "
            "<code>https://udb.example.org/api/external_interface/contracts/</code>. "
            "Filters and requested fields are appended by the code (a static JSON file simply ignores them)."
        ),
    )
    api_token = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="UDB API token",
        help_text="Sent as the <code>X-API-KEY</code> header. Stored in plaintext in the database.",
    )

    class Meta:
        verbose_name = "UDB Sync Configuration"
        verbose_name_plural = "UDB Sync Configuration"

    def __str__(self):
        return "UDB Sync Configuration"

    def clean(self):
        super().clean()
        if "?" in self.url:
            raise ValidationError(
                {"url": "Provide the URL without a query string ('?...'). The query is appended by the code."}
            )
