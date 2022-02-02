from django.db import models

from ..utils.bulk_management import import_data, validate_csv


class ImporterList(models.Model):

    VALID_COL_HEADERS = [
        'SAP_ID',
        'ROOM',
        'EDV_ID',
        'DEVICE_TYPE',
        'SERIAL_NUMBER',
        'MANUFACTURER',
        'SERIES',
        'SUPPLIER',
        'PURCHASE_DATE',
        'WARRANTY_EXPIRATION_DATE',
        'MAINTENANCE_CONTRACT_EXPIRATION_DATE',
        'COST_CENTRE',
        'BOOK_VALUE',
        'NOTE',
        'MAC_ADDRESS',
        'EXTRA_MAC_ADDRESSES',
        'NICK_NAME',
        'IS_LENTABLE',
        'IS_LICENCE',
        'USERNAME',
        'TENANT',
    ]

    DATE_FIELDS = [
        'PURCHASE_DATE',
        'WARRANTY_EXPIRATION_DATE',
        'MAINTENANCE_CONTRACT_EXPIRATION_DATE',
    ]

    file = models.FileField(
        upload_to='imported_csv',
        verbose_name='CSV-Datei',
        help_text='Valide Spaltenköpfe: <br>{}'.format("<br>".join(VALID_COL_HEADERS)),
    )
    note = models.TextField(null=True, blank=True, verbose_name='Anmerkung')
    messages = models.TextField(
        blank=True,
        verbose_name='DLCDB-Ausgaben zu diesem Import',
        editable=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Erstellt',
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Geändert',
    )

    class Meta:
        verbose_name = 'Import-Datei'
        verbose_name_plural = 'Import-Dateien'
        ordering = ['-modified_at', '-created_at']

    def __str__(self):
        return '{}'.format(self.file)

    def clean(self):
        print("[model clean] Checking CSV file:", self.file)
        validate_csv(
            self.file,
            valid_col_headers=self.VALID_COL_HEADERS,
            date_fields=self.DATE_FIELDS,
            bulk_mode='import_devices',
        )

    def save(self, *args, **kwargs):
        print("[model save] Importing CSV file:", self.file)
        
        adding = False
        if self._state.adding is True:
            adding = True

        super().save(*args, **kwargs)

        if adding is True:
            # Importing after super().save() in order to have an already saved
            # ImporterList instance, as we set this as a related field on Device.
            self.messages = import_data(self.file, importer_inst_pk=self.pk)
            self.save(update_fields=['messages'])
