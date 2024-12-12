# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
# from django.db.models import Max

from ..core.models import Record


class Subscription(models.Model):
    class NotificationEventChoices(models.TextChoices):
        # License related
        CONTRACT_ADDED = "CONTRACT_ADDED", "Contract Added"
        CONTRACT_EXPIRES_SOON = "CONTRACT_EXPIRES_SOON", "Contract Expires Soon"
        CONTRACT_EXPIRED = "CONTRACT_EXPIRED", "Contract Expired"
        # Location related
        MOVED = "MOVED", "Moved"
        # Device related
        DEVICE_DECOMMISSIONED = "DEVICE_DECOMMISSIONED", "Device decommissioned"

    event = models.CharField(
        max_length=255,
        choices=NotificationEventChoices.choices,
        blank=False,
        verbose_name=_("Type of event"),
    )

    class NotificationIntervalChoices(models.TextChoices):
        IMMEDIATELY = "immediately", "Immediately"
        HOURLY = "hourly", "Every Hour"
        DAILY = "daily", "Every Day"
        WEEKLY = "weekly", "Every Week"
        MONTHLY = "monthly", "Every Month"
        YEARLY = "yearly", "Every Year"

    interval = models.CharField(
        max_length=255,
        blank=False,
        choices=NotificationIntervalChoices.choices,
        verbose_name=_("Interval Name"),
    )

    subscriber = models.ForeignKey("core.Person", on_delete=models.PROTECT)
    device = models.ForeignKey("core.Device", on_delete=models.PROTECT, null=True, blank=True)
    # last_sent = models.DateTimeField(null=True, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # @property
    # def last_sent(self):
    #     """Calculate last sent time from messages"""
    #     return self.message_set.filter(status="sent").aggregate(Max("sent_at"))["sent_at__max"]

    def __str__(self):
        return "{id} {active} | {event} → {interval} → {subscriber}".format(
            id=self.id,
            active="✓" if self.is_active else "✗",
            event=self.event,
            interval=self.interval,
            subscriber=self.subscriber,
        )


class Message(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.subscription.user.username} about {self.subscription.event.name}"

    class Meta:
        ordering = ["-created_at"]

    # def send(self):
    #     try:
    #         send_mail(
    #             subject=self.template.subject,
    #             message=self.template.body,
    #             from_email=settings.DEFAULT_FROM_EMAIL,
    #             recipient_list=[self.recipient_email],
    #             fail_silently=False,
    #         )
    #         self.status = 'sent'
    #         self.sent_at = timezone.now()
    #     except Exception as e:
    #         self.status = 'failed'
    #         self.error_message = str(e)
    #     self.save()


# Legacy notification implementation
# TODO: Migrate to new implementation


class Notification(models.Model):
    EVERY_MINUTE = "EVERY_MINUTE"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"
    TIME_INTERVAL_CHOICES = [
        (DAILY, "Täglich"),
        (WEEKLY, "Wöchentlich"),
        (MONTHLY, "Monatlich"),
        (YEARLY, "Jährlich"),
        (EVERY_MINUTE, "Minütlich"),
    ]

    IS_NEW_PC_OR_NOTEBOOK = "IS_NEW_PC_OR_NOTEBOOK"
    IS_PC_OR_NOTEBOOK = "IS_PC_OR_NOTEBOOK"
    IS_PC = "IS_PC"
    IS_NOTEBOOK = "IS_NOTEBOOK"
    HAS_SAP_ID = "HAS_SAP_ID"
    LENT_IS_OVERDUE = "LENT_IS_OVERDUE"
    LICENCE_EXPIRES = "LICENCE_EXPIRES"
    CONDITION_CHOICES = [
        (LENT_IS_OVERDUE, "Rückgabe überfällig"),
        (IS_NEW_PC_OR_NOTEBOOK, "Ist neuer PC oder Notebook"),
        (IS_PC_OR_NOTEBOOK, "Ist PC oder Notebook"),
        (IS_PC, "Ist PC"),
        (IS_NOTEBOOK, "Ist Notebook"),
        (HAS_SAP_ID, "Hat SAP-Nummer"),
        (LICENCE_EXPIRES, "Lizenz läuft ab"),
    ]

    active = models.BooleanField(
        default=True,
        verbose_name="Aktiv?",
    )
    recipient = models.EmailField(
        blank=False,
        verbose_name="Empfänger (Email To)",
    )
    recipient_cc = models.EmailField(
        blank=True,
        verbose_name="Empfänger (Email CC)",
    )
    event = models.CharField(
        max_length=20,
        choices=Record.RECORD_TYPE_CHOICES,
        blank=False,
        verbose_name="Ereignis",
    )
    condition = models.CharField(
        max_length=255,
        choices=CONDITION_CHOICES,
        blank=True,
        verbose_name="Bedingung",
    )
    device = models.ForeignKey(
        "core.Device",
        null=True,
        blank=True,
        help_text="Für Gerätebezogene Benachrichtigungen",
        on_delete=models.SET_NULL,
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
        verbose_name="Benachrichtigungen ohne Updates",
        help_text="Benachrichtigungen erhalten, auch wenn keine Veränderungen stattgefunden haben. Nützlich, um die Email-Funktionalität zu testen.",
    )

    def clean(self):
        _errors = []
        already_exists = (
            Notification.objects.exclude(pk=self.pk)
            .filter(
                event=self.event,
                condition=self.condition,
                time_interval=self.time_interval,
            )
            .exists()
        )

        if already_exists:
            _errors.append(
                ValidationError(
                    "Es existiert schon eine Notification für diesen Zweck. Bitte tragen Sie sich dort ein.",
                    code="invalid",
                )
            )

        if (self.condition == self.LENT_IS_OVERDUE) and (self.event != Record.LENT):
            _errors.append(
                ValidationError(
                    'Überfälligkeitsnachrichten können nur für "Ausleihen" erstellt werden.', code="invalid"
                )
            )

        if (not settings.DEBUG) and (self.time_interval == self.EVERY_MINUTE):
            _errors.append(ValidationError("Minütlicher Tasks nur im development Modus erlaubt.", code="invalid"))

        if _errors:
            raise ValidationError(_errors)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return "{active} | {event}/{condition} → {interval} → {recipient}".format(
            active="✓" if self.active else "✗",
            event=self.event,
            condition=self.condition if self.condition else "",
            interval=self.time_interval,
            recipient=self.recipient,
        )

    class Meta:
        verbose_name = "Benachrichtigung"
        verbose_name_plural = "Benachrichtigungen"


def spreadsheet_directory_path(instance, filename):
    return "reporting/spreadsheets/{0}".format(filename)


class Report(models.Model):
    notification = models.ForeignKey(
        "Notification",
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
            self.notification.event if self.notification else "",
        )

    class Meta:
        verbose_name = "Report"
        verbose_name_plural = "Reports"
