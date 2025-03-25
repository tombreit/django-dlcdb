from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.sites.models import Site
from django.template.loader import render_to_string

from simple_history.models import HistoricalRecords
from .intervals import NotificationInterval, INTERVAL_DETAILS


# class SubscriptionManager(models.Manager):
#     def get_or_create_license_subscription(self, subscriber, device, interval=NotificationInterval.IMMEDIATELY.value):
#         """Create subscriptions for all license events for a specific subscriber and device"""
#         result = []

#         for license_event in Subscription.LICENSE_EVENTS:
#             subscription, created = self.get_or_create(
#                 event=license_event,
#                 subscriber=subscriber,
#                 device=device,
#                 interval=interval,  # Default is IMMEDIATELY
#             )
#             result.append(
#                 {
#                     "subscription": subscription,
#                     "created": created,
#                 }
#             )

#         return result

#     def delete_license_subscriptions(self, subscriber, device):
#         result = []
#         for license_event in Subscription.LICENSE_EVENTS:
#             subscription = self.filter(
#                 event=license_event,
#                 subscriber=subscriber,
#                 device=device,
#             ).delete()

#             result.append(
#                 {
#                     "subscription": subscription,
#                     "deleted": True,
#                 }
#             )

#         return result


class Subscription(models.Model):
    history = HistoricalRecords()
    objects = models.Manager()
    # custom_objects = SubscriptionManager()

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
        blank=True,
        verbose_name=_("Type of event"),
    )

    LICENSE_EVENTS = [
        NotificationEventChoices.CONTRACT_ADDED,
        NotificationEventChoices.CONTRACT_EXPIRES_SOON,
        NotificationEventChoices.CONTRACT_EXPIRED,
    ]

    interval = models.CharField(
        max_length=255,
        blank=True,
        choices=[(interval.value, INTERVAL_DETAILS[interval]["display_name"]) for interval in NotificationInterval],
        verbose_name=_("Interval Name"),
    )

    subscriber = models.ForeignKey("core.Person", on_delete=models.PROTECT, blank=True, null=True)
    device = models.ForeignKey("core.Device", on_delete=models.PROTECT, null=True, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    last_sent = models.DateTimeField(null=True, blank=True)
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

    def save(self, *args, **kwargs):
        # Schedule next notification when creating/updating
        if not self.next_scheduled:
            self.schedule_next_message()
        super().save(*args, **kwargs)

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
        """Create a message for this subscription"""
        return Message.objects.get_or_create(subscription=self)

    def __str__(self):
        return "{id} {active} | {device}: {event} → {interval} → {subscriber}".format(
            id=self.id,
            active="✓" if self.is_active else "✗",
            device=self.device,
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

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    # Message content fields
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

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
        context = {
            "subscription": subscription,
            "subscriber": subscription.subscriber,
            "device": subscription.device,
            "subject_prefix": settings.EMAIL_SUBJECT_PREFIX if hasattr(settings, "EMAIL_SUBJECT_PREFIX") else "",
        }

        # Add event-specific data to context
        if subscription.event in subscription.LICENSE_EVENTS and subscription.device:
            # For license events, include contract details
            domain = Site.objects.get_current().domain
            url_path = reverse("licenses:edit", args=[subscription.device.id])
            context["license_url"] = f"https://{domain}{url_path}"

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
        return f"{self.id} - {self.status} - {self.subscription}"

    class Meta:
        ordering = ["-modified_at"]
