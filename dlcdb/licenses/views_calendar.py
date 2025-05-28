from datetime import timedelta
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.http import Http404

import icalendar
from icalendar import Calendar, Event

from dlcdb.notifications.models import Subscription
from .models import LicenseAsset


def _add_license_ical_event(cal, device, date, event_type, prefix=None, add_alarm=False):
    """Utility function to add an event to the calendar"""
    if date is None:
        return None

    # Try to get content from notification templates
    summary, description = _get_notification_content_for_event(device, event_type)

    # Fallback if template rendering fails
    if not summary:
        device_id = device.sap_id or device.edv_id or str(device.uuid)

        if event_type == "start":
            summary = f"License Contract Start: {device_id}"
            description = f"License contract starts for {device_id}"
        elif event_type == "expiry":
            summary = f"License Contract Expiration: {device_id}"
            description = f"License contract expires for {device_id}"
        elif event_type == "reminder":
            summary = f"License Expiring Soon: {device_id}"
            description = f"License contract for {device_id} expires on {device.contract_expiration_date}"
        else:
            summary = f"{prefix or 'License Event'}: {device_id}"
            description = f"License event for {device_id}"

    event = Event()
    event.add("summary", summary)
    event.add("description", description)

    # Handle date vs datetime
    if hasattr(date, "hour"):
        # It's a datetime object
        event.add("dtstart", date)
    else:
        # It's a date object, not datetime - make it an all-day event
        event.add("dtstart", date)

        # Add end date as the next day (icalendar standard: end date is exclusive)
        import datetime

        next_day = date + datetime.timedelta(days=1)
        event.add("dtend", next_day)

        # For Microsoft Outlook compatibility
        event.add("x-microsoft-cdo-alldayevent", "TRUE")

    # Add unique ID
    event["uid"] = f"{event_type}-{device.uuid}@dlcdb.example.org"

    # Add alarm if requested
    if add_alarm:
        alarm = icalendar.Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Reminder: {summary}")
        alarm.add("trigger", timedelta(days=-5))
        event.add_component(alarm)

    # Add event to calendar
    cal.add_component(event)

    return event


def _get_notification_content_for_event(device, event_type):
    """
    Get summary and description for calendar event by reusing notification templates
    """
    # Map calendar event types to notification event types
    event_map = {
        "start": Subscription.NotificationEventChoices.CONTRACT_ADDED,
        "expiry": Subscription.NotificationEventChoices.CONTRACT_EXPIRED,
    }

    notification_event = event_map.get(event_type)
    if not notification_event:
        return None, None

    # Get template paths from notification system
    templates = {
        "subject": "notifications/emails/contract_subject.txt",
        "body": "notifications/emails/contract_body.txt",
    }

    # Build context with available data - similar to what Message.generate_content does
    context = {
        "device": device,
        "subscription": {"event": notification_event},  # Mock subscription object with required fields
    }

    # Render the templates
    subject = render_to_string(templates["subject"], context).strip()
    body = render_to_string(templates["body"], context).strip()

    return subject, body


@login_required
def license_calendar(request, license_uuid):
    """Generate an iCal file for a specific license"""
    device = get_object_or_404(LicenseAsset, uuid=license_uuid)

    # Check if there are any events to show
    if not device.contract_start_date and not device.contract_expiration_date:
        raise Http404("No calendar events available for this license")

    # Create calendar
    cal = Calendar()
    cal.add("prodid", "-//DLCDB License Calendar//dlcdb.example.org//")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", f"DLCDB License: {device.sap_id or device.edv_id or device.uuid}")

    # Add contract start event
    if device.contract_start_date:
        _add_license_ical_event(cal, device, device.contract_start_date, "start")

    # Add expiration events
    if device.contract_expiration_date:
        _add_license_ical_event(cal, device, device.contract_expiration_date, "expiry")

    # Generate the calendar file
    calendar_content = cal.to_ical()

    # Create the response with the calendar data
    response = HttpResponse(calendar_content, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="license_{device.id}_calendar.ics"'

    return response
