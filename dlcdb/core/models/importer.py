from django.db import models


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

    file = models.FileField(
        upload_to='imported_csv',
        verbose_name='CSV-Datei',
        help_text='Valide Spaltenköpfe: <br>{}'.format("<br>".join(VALID_COL_HEADERS)),
    )
    note = models.TextField(
        null=True,
        blank=True,
        verbose_name='Anmerkung',
    )
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
