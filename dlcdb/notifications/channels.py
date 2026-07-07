# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import logging
import os

from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMessage

from .models import Message

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

logger = logging.getLogger(__name__)


# Move this to module level
def mark_message_failed(message, error_message):
    """Mark a message as failed with an error"""
    message.status = Message.STATUS_FAILED
    message.error_message = error_message
    message.save()


class NotificationChannel:
    """Base class for notification channels"""

    @classmethod
    def send(cls, message):
        """
        Send a notification via this channel

        Args:
            message: Message instance

        Returns:
            bool: Success status
        """
        raise NotImplementedError("Subclasses must implement send method")


class EmailChannel(NotificationChannel):
    """Email notification channel"""

    @classmethod
    def send(cls, message):
        """Send notification via email"""
        try:
            subject, body = message.get_content()
            to = message.get_recipients()

            # Without this guard, EmailMessage.send() with no recipients
            # silently sends nothing and the message would be marked SENT.
            if not to:
                mark_message_failed(message, "No recipient email address")
                logger.warning(f"No recipient email address for message {message.id}")
                return False

            email = EmailMessage(
                subject=f"{settings.EMAIL_SUBJECT_PREFIX} {subject}",
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=to,
            )

            # Attach the report spreadsheet, if any. Read via the storage
            # API, so this also works for non-filesystem storages.
            if message.report and message.report.spreadsheet:
                email.attach(
                    os.path.basename(message.report.spreadsheet.name),
                    message.report.spreadsheet.read(),
                    XLSX_CONTENT_TYPE,
                )

            email.send(fail_silently=False)

            message.status = Message.STATUS_SENT
            message.sent_at = timezone.now()
            message.save()
            logger.info(f"Email sent for message {message.id} to {to}")
            return True

        except Exception as e:
            mark_message_failed(message, str(e))  # Use the module-level function
            logger.exception(f"Failed to send email for message {message.id}: {str(e)}")
            return False


# Registry of available channels
CHANNELS = {
    "email": EmailChannel,
    # Add more channels here as they're implemented
    # 'sms': SMSChannel,
    # 'slack': SlackChannel,
}


def send_via_all_channels(message):
    """
    Send a message through all available channels

    Args:
        message: Message instance

    Returns:
        bool: True if any channel succeeded
    """
    success = False

    for channel_name, channel_class in CHANNELS.items():
        try:
            channel_success = channel_class.send(message)
            if channel_success:
                success = True
        except Exception as e:
            logger.exception(f"Error in {channel_name} channel for message {message.id}: {str(e)}")

    return success
