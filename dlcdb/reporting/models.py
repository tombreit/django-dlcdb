from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..core.models import Record


class Notification(models.Model):

    EVERY_MINUTE = 'EVERY_MINUTE'
    DAILY = 'DAILY'
    WEEKLY = 'WEEKLY'
    MONTHLY = 'MONTHLY'
    YEARLY = 'YEARLY'
    TIME_INTERVAL_CHOICES = [
        (DAILY, 'Täglich'),
        (WEEKLY, 'Wöchentlich'),
        (MONTHLY, 'Monatlich'),
        (YEARLY, 'Jährlich'),
        (EVERY_MINUTE, 'Minütlich'),
    ]

    IS_NEW_PC_OR_NOTEBOOK = 'IS_NEW_PC_OR_NOTEBOOK'
    IS_PC_OR_NOTEBOOK = 'IS_PC_OR_NOTEBOOK'
    IS_PC = 'IS_PC'
    IS_NOTEBOOK = 'IS_NOTEBOOK'
    HAS_SAP_ID = 'HAS_SAP_ID'
    LENT_IS_OVERDUE = 'LENT_IS_OVERDUE'
    CONDITION_CHOICES = [
        (LENT_IS_OVERDUE, 'Rückgabe überfällig'),
        (IS_NEW_PC_OR_NOTEBOOK, 'Ist neuer PC oder Notebook'),
        (IS_PC_OR_NOTEBOOK, 'Ist PC oder Notebook'),
        (IS_PC, 'Ist PC'),
        (IS_NOTEBOOK, 'Ist Notebook'),
        (HAS_SAP_ID, 'Hat SAP-Nummer'),
    ]

    active = models.BooleanField(
        default=True,
        verbose_name='Aktiv?',
    )
    recipient = models.EmailField(
        blank=False,
        verbose_name='Empfänger (Email To)',
    )
    recipient_cc = models.EmailField(
        blank=True,
        verbose_name='Empfänger (Email CC)',
    )
    event =  models.CharField(
        max_length=20,
        choices=Record.RECORD_TYPE_CHOICES,
        blank=False,
        verbose_name='Ereignis',
    )
    condition =  models.CharField(
        max_length=255,
        choices=CONDITION_CHOICES,
        blank=True,
        verbose_name='Bedingung',
    )
    time_interval = models.CharField(
        max_length=255,
        choices=TIME_INTERVAL_CHOICES,
        default=WEEKLY,
    )
    last_run = models.DateTimeField(
        null=True,
        blank=True,
    )
    notify_no_updates = models.BooleanField(
        default=False,
        verbose_name='Benachrichtigungen ohne Updates',
        help_text='Benachrichtigungen erhalten, auch wenn keine Veränderungen stattgefunden haben. Nützlich, um die Email-Funktionalität zu testen.'
    )

    def clean(self):
        _errors = []
        already_exists = (
            Notification
            .objects
            .exclude(pk=self.pk)
            .filter(
                event=self.event,
                condition=self.condition,
                time_interval=self.time_interval,
            ).exists()
        )

        if already_exists:
            _errors.append(
                ValidationError('Es existiert schon eine Notification für diesen Zweck. Bitte tragen Sie sich dort ein.', code='invalid')
            )

        if (self.condition == self.LENT_IS_OVERDUE) and (self.event != Record.LENT):
            _errors.append(
                ValidationError('Überfälligkeitsnachrichten können nur für "Ausleihen" erstellt werden.', code='invalid')
            )

        if (not settings.DEBUG) and (self.time_interval == self.EVERY_MINUTE):
            _errors.append(
                ValidationError('Minütlicher Tasks nur im development Modus erlaubt.', code='invalid')
            )

        if _errors:
            raise ValidationError(_errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return '{active} | {event}/{condition} → {interval} → {recipient}'.format(
            active='✓' if self.active else '✗',
            event=self.event,
            condition=self.condition if self.condition else '',
            interval=self.time_interval,
            recipient=self.recipient,
        )

    class Meta:
        verbose_name = 'Benachrichtigung'
        verbose_name_plural = 'Benachrichtigungen'


def spreadsheet_directory_path(instance, filename):
    return 'reporting/spreadsheets/{0}'.format(filename)


class Report(models.Model):
    notification = models.ForeignKey(
        'Notification',
        null=True,
        blank=False,
        on_delete=models.SET_NULL,
    )
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
        verbose_name='Erstellt',
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Geändert',
    )

    def __str__(self):
        return '{0}: {1} {2}'.format(
            self.pk,
            timezone.localtime(self.created_at),
            self.notification.event if self.notification else '',
        )

    class Meta:
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'
