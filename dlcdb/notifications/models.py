# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string

from simple_history.models import HistoricalRecords

from .email_footer import email_footer_context
from .intervals import NotificationInterval, INTERVAL_DETAILS


class Subscription(models.Model):
    """
    A subscriber's standing interest in an event, delivered as Messages.

    Two kinds of subscriptions, branched by the event:
    - device events (contract/license, moved, decommissioned): about one
      specific device, requires `device`.
    - report events (record types like INROOM or LENT): a periodic report
      about all records matching `condition`, delivered with an xlsx
      spreadsheet attachment.
    """

    history = HistoricalRecords()
    objects = models.Manager()

    class NotificationEventChoices(models.TextChoices):
        # Device events: about one specific device
        CONTRACT_ADDED = "CONTRACT_ADDED", "Contract Added"
        CONTRACT_EXPIRES_SOON = "CONTRACT_EXPIRES_SOON", "Contract Expires Soon"
        CONTRACT_EXPIRED = "CONTRACT_EXPIRED", "Contract Expired"
        MOVED = "MOVED", "Moved"
        DEVICE_DECOMMISSIONED = "DEVICE_DECOMMISSIONED", "Device decommissioned"
        # Report events: periodic report about records of this record type
        ORDERED = "ORDERED", "Report: Ordered devices"
        INROOM = "INROOM", "Report: Located devices"
        LENT = "LENT", "Report: Lent devices"
        LOST = "LOST", "Report: Lost devices"
        REMOVED = "REMOVED", "Report: Removed devices"

    LICENSE_EVENTS = [
        NotificationEventChoices.CONTRACT_ADDED,
        NotificationEventChoices.CONTRACT_EXPIRES_SOON,
        NotificationEventChoices.CONTRACT_EXPIRED,
    ]

    # Values equal Record.record_type, so report record selection can filter
    # record_type=subscription.event directly.
    REPORT_EVENTS = [
        NotificationEventChoices.ORDERED,
        NotificationEventChoices.INROOM,
        NotificationEventChoices.LENT,
        NotificationEventChoices.LOST,
        NotificationEventChoices.REMOVED,
    ]

    class ConditionChoices(models.TextChoices):
        LENT_IS_OVERDUE = "LENT_IS_OVERDUE", _("Return overdue")
        IS_NEW_PC_OR_NOTEBOOK = "IS_NEW_PC_OR_NOTEBOOK", _("Is new PC or notebook")
        IS_PC_OR_NOTEBOOK = "IS_PC_OR_NOTEBOOK", _("Is PC or notebook")
        IS_PC = "IS_PC", _("Is PC")
        IS_NOTEBOOK = "IS_NOTEBOOK", _("Is notebook")
        HAS_SAP_ID = "HAS_SAP_ID", _("Has SAP number")
        LICENCE_EXPIRES = "LICENCE_EXPIRES", _("Licence expires")

    event = models.CharField(
        max_length=255,
        choices=NotificationEventChoices.choices,
        verbose_name=_("Type of event"),
    )
    condition = models.CharField(
        max_length=255,
        choices=ConditionChoices.choices,
        blank=True,
        verbose_name=_("Condition"),
        help_text=_("Only for report events: restrict which records are reported."),
    )
    interval = models.CharField(
        max_length=255,
        choices=[(interval.value, INTERVAL_DETAILS[interval]["display_name"]) for interval in NotificationInterval],
        default=NotificationInterval.WEEKLY.value,
        verbose_name=_("Interval"),
    )

    subscriber = models.ForeignKey("core.Person", on_delete=models.PROTECT)
    device = models.ForeignKey("core.Device", on_delete=models.PROTECT, null=True, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    notify_no_updates = models.BooleanField(
        default=False,
        verbose_name=_("Notify without updates"),
        help_text=_("Also send an email when no records match. Useful for testing the email functionality."),
    )

    last_sent = models.DateTimeField(null=True, blank=True)
    # Report window anchor: reports cover records since last_run. Only
    # advanced by scheduled processing, never by ad-hoc admin triggers.
    last_run = models.DateTimeField(null=True, blank=True)
    next_scheduled = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "When the next message should be sent. Based on the interval setting. "
            "Subscriptions with a date/time in the past are due for processing."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def is_report_subscription(self):
        return self.event in self.REPORT_EVENTS

    def save(self, *args, **kwargs):
        # Schedule next notification when creating/updating
        if not self.next_scheduled:
            self.schedule_next_message()
        super().save(*args, **kwargs)

    def clean(self):
        errors = []

        if self.is_report_subscription:
            if self.device:
                errors.append(ValidationError(_("Report subscriptions are not device-specific."), code="invalid"))
            if self.interval == NotificationInterval.POINT_IN_TIME.value:
                errors.append(ValidationError(_("Report subscriptions need a recurring interval."), code="invalid"))
            if not settings.DEBUG and self.interval in [
                NotificationInterval.IMMEDIATELY.value,
                NotificationInterval.HOURLY.value,
            ]:
                errors.append(
                    ValidationError(
                        _("Immediately/hourly intervals are only allowed in development mode."), code="invalid"
                    )
                )
            if (
                self.condition == self.ConditionChoices.LENT_IS_OVERDUE
                and self.event != self.NotificationEventChoices.LENT
            ):
                errors.append(
                    ValidationError(_('Overdue notifications can only be created for "lent" records.'), code="invalid")
                )
            already_exists = (
                Subscription.objects.exclude(pk=self.pk)
                .filter(subscriber=self.subscriber, event=self.event, condition=self.condition, interval=self.interval)
                .exists()
            )
            if already_exists:
                errors.append(ValidationError(_("You already have a subscription for this report."), code="invalid"))
        else:
            if self.condition:
                errors.append(
                    ValidationError(_("Conditions are only available for report subscriptions."), code="invalid")
                )
            if not self.device:
                errors.append(ValidationError(_("Device subscriptions need a device."), code="invalid"))
            already_exists = (
                Subscription.objects.exclude(pk=self.pk)
                .filter(subscriber=self.subscriber, event=self.event, device=self.device)
                .exists()
            )
            if already_exists:
                errors.append(
                    ValidationError(_("You already have a subscription for this event and device."), code="invalid")
                )

        if errors:
            raise ValidationError(errors)

    def schedule_next_message(self, datetime_obj=None):
        """
        Update tracking of when messages were sent and when next ones are due.

        Args:
            datetime_obj: Optional specific datetime to schedule for. If provided,
                         this overrides the interval-based scheduling.
        """
        if datetime_obj:
            self.next_scheduled = datetime_obj
        else:
            now = timezone.now()
            interval_enum = NotificationInterval(self.interval)
            self.next_scheduled = INTERVAL_DETAILS[interval_enum]["schedule_function"](now)

    def create_message(self):
        """Create a message for this subscription, reusing a pending one."""
        return Message.objects.get_or_create(subscription=self, status=Message.STATUS_PENDING)

    def __str__(self):
        return "{id} {active} | {target}: {event} → {interval} → {subscriber}".format(
            id=self.id,
            active="✓" if self.is_active else "✗",
            target=self.condition if self.is_report_subscription else self.device,
            event=self.event,
            interval=self.interval,
            subscriber=self.subscriber,
        )


class Message(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    # A message originates either from a Subscription or is standalone with
    # an explicit recipient_email (e.g. overdue lender mails).
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # Message content fields
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    # Explicit recipient for standalone messages; when empty, the
    # subscription's subscriber is used.
    recipient_email = models.EmailField(blank=True)
    # Optional CC (e.g. IT on overdue lender mails).
    cc_email = models.EmailField(blank=True)

    # Report artifact whose spreadsheet gets attached to the email.
    report = models.ForeignKey("reporting.Report", on_delete=models.SET_NULL, null=True, blank=True)

    def get_recipients(self) -> list[str]:
        """Return the recipient email addresses for this message."""
        if self.recipient_email:
            return [self.recipient_email]
        subscriber_email = self.subscription.subscriber.get_email
        return [subscriber_email] if subscriber_email else []

    # Add the method to generate content
    def generate_content(self, force: bool = False) -> tuple[str, str]:
        """
        Generate the message content (subject and body)

        Args:
            force: If True, regenerate even if content already exists

        Returns:
            tuple: (subject, body)
        """
        # Skip generation if content already exists and force=False
        if not force and self.subject and self.body:
            return self.subject, self.body

        # Only device subscription messages render templates; report and
        # standalone messages get their content authored at creation time.
        if self.subscription is None or self.subscription.is_report_subscription:
            return self.subject, self.body

        subscription = self.subscription

        # Map of event types to template paths
        templates = {
            subscription.NotificationEventChoices.CONTRACT_ADDED: {
                "subject": "notifications/emails/contract_subject.txt",
                "body": "notifications/emails/contract_body.txt",
            },
            subscription.NotificationEventChoices.CONTRACT_EXPIRES_SOON: {
                "subject": "notifications/emails/contract_subject.txt",
                "body": "notifications/emails/contract_body.txt",
            },
            subscription.NotificationEventChoices.CONTRACT_EXPIRED: {
                "subject": "notifications/emails/contract_subject.txt",
                "body": "notifications/emails/contract_body.txt",
            },
            subscription.NotificationEventChoices.MOVED: {
                "subject": "notifications/emails/device_moved_subject.txt",
                "body": "notifications/emails/device_moved_body.txt",
            },
            subscription.NotificationEventChoices.DEVICE_DECOMMISSIONED: {
                "subject": "notifications/emails/device_decommissioned_subject.txt",
                "body": "notifications/emails/device_decommissioned_body.txt",
            },
        }

        template_data = templates.get(
            subscription.event,
            {
                "subject": "notifications/emails/default_subject.txt",
                "body": "notifications/emails/default_body.txt",
            },
        )

        # Build context with available data
        # Note: the subject prefix (settings.EMAIL_SUBJECT_PREFIX) is added by
        # the email channel on send, not here.
        context = {
            "subscription": subscription,
            "subscriber": subscription.subscriber,
            "device": subscription.device,
            **email_footer_context(),
        }

        # Render the templates
        self.subject = render_to_string(template_data["subject"], context).strip()
        self.body = render_to_string(template_data["body"], context)
        self.save(update_fields=["subject", "body"])

        return self.subject, self.body

    def get_content(self):
        """
        Get message content, generating it if necessary

        Returns:
            tuple: (subject, body)
        """
        if not self.subject or not self.body:
            return self.generate_content()
        return self.subject, self.body

    def get_preview_content(self):
        """
        Get or generate content for admin preview

        Returns:
            dict: Content with keys 'subject' and 'body'
        """
        try:
            subject, body = self.get_content()
            return {
                "subject": subject,
                "body": body,
            }
        except Exception as e:
            return {
                "subject": "Error: Could not generate subject",
                "body": f"Error generating message content: {str(e)}",
                "error": str(e),
            }

    def __str__(self):
        origin = self.subscription or self.recipient_email
        return f"{self.id} - {self.status} - {origin}"

    class Meta:
        ordering = ["-modified_at"]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(subscription__isnull=False) | ~models.Q(recipient_email="")),
                name="message_has_recipient_source",
            ),
        ]
