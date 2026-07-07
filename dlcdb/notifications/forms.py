# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.conf import settings
from django.db.models.fields import BLANK_CHOICE_DASH

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row

from .intervals import INTERVAL_DETAILS, NotificationInterval
from .models import Subscription


class ReportSubscriptionForm(forms.ModelForm):
    """
    User-facing form for report subscriptions. The subscriber is never a form
    field: the view passes an unsaved Subscription(subscriber=person) instance
    so the model clean() (uniqueness etc.) sees it during validation.
    """

    class Meta:
        model = Subscription
        fields = ["event", "condition", "interval", "notify_no_updates"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["event"].choices = BLANK_CHOICE_DASH + [(e.value, e.label) for e in Subscription.REPORT_EVENTS]

        # LICENCE_EXPIRES is only used by license subscriptions.
        self.fields["condition"].choices = [
            (value, label)
            for value, label in self.fields["condition"].choices
            if value != Subscription.ConditionChoices.LICENCE_EXPIRES
        ]

        # Mirror the intervals the model clean() accepts for report
        # subscriptions (evaluated at request time, not import time, so
        # DEBUG overrides in tests take effect).
        excluded_intervals = {NotificationInterval.POINT_IN_TIME}
        if not settings.DEBUG:
            excluded_intervals |= {NotificationInterval.IMMEDIATELY, NotificationInterval.HOURLY}
        self.fields["interval"].choices = [
            (interval.value, INTERVAL_DETAILS[interval]["display_name"])
            for interval in NotificationInterval
            if interval not in excluded_intervals
        ]

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column("event", css_class="col-md-3"),
                Column("condition", css_class="col-md-3"),
                Column("interval", css_class="col-md-3"),
                Column("notify_no_updates", css_class="col-md-3 align-self-center"),
            ),
        )
