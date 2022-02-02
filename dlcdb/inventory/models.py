import os.path

from django.conf import settings
from django.db import models


class SapList(models.Model):
    file = models.FileField(upload_to='sap_csv', verbose_name='CSV-Datei')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Erstellungsdatum')
    note = models.TextField(null=True, blank=True, verbose_name='Anmerkung')

    class Meta:
        verbose_name = 'SAP-Liste'
        verbose_name_plural = 'SAP-Listen'

    def get_file_name(self):
        return self.file.name.split('/')[-1]


class SapListComparisonResult(models.Model):
    sap_list = models.ForeignKey(SapList, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)

    def get_url(self):
        if self.file_name:
            return os.path.join(
                settings.MEDIA_URL,
                settings.SAP_LIST_COMPARISON_RESULT_FOLDER,
                self.file_name
            )
