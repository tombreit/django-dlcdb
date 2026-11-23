# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import re

from django.core.exceptions import ValidationError
from django.db import models
from django.template import Template, TemplateSyntaxError
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from ..core.models.abstracts import SingletonBaseModel
from .starter import get_starter_lending_preparation_checklist, get_starter_lent_sheet_template

# Script in a slip template or checklist: a script element, an on… event
# attribute or a javascript: URL. The printed slip runs none anyway
# (lending.views.SLIP_POLICY), also none this misses; saving refuses them so
# the author knows.
SCRIPT_RE = re.compile(r"<script\b|<[^>]*\son[a-z]+\s*=|javascript:", re.IGNORECASE)


class LendingConfiguration(SingletonBaseModel):
    class OverdueNotificationRecipient(models.TextChoices):
        NONE = "none", _("Nobody — no overdue mails")
        LENDER = "lender", _("Lender")
        LENDER_AND_IT = "lender_and_it", _("Lender, IT in CC")
        IT = "it", _("IT only (testdrive: lender mails rerouted to IT)")

    overdue_notifications_recipient = models.CharField(
        max_length=20,
        choices=OverdueNotificationRecipient.choices,
        default=OverdueNotificationRecipient.LENDER,
        verbose_name=_("Overdue reminders to"),
        help_text=_(
            "Who receives the weekly overdue-lending reminder mails. The IT address is "
            "resolved per tenant: tenant contact email → the IT department email under Settings › Organization "
            "→ DEFAULT_FROM_EMAIL."
        ),
    )

    def __str__(self):
        return "Lending Configuration"

    class Meta:
        verbose_name = _("Lending configuration")
        verbose_name_plural = _("Lending configuration")


class LendingProfileRegulation(models.Model):
    lending_profile = models.ForeignKey("lending.LendingProfile", on_delete=models.CASCADE)
    # PROTECT: a regulation a profile requires can't silently drop off its slips.
    regulation = models.ForeignKey("core.Link", on_delete=models.PROTECT)

    class Meta:
        unique_together = ("lending_profile", "regulation")

    def __str__(self):
        return f"LendingProfile ({self.lending_profile.device_type}) - {self.regulation.linktext}"


class LendingProfile(models.Model):
    device_type = models.OneToOneField(
        "core.DeviceType",
        on_delete=models.CASCADE,
        related_name="lending_profile",
        verbose_name=_("Device type"),
    )
    lending_preparation_checklist = models.TextField(
        blank=True,
        default=get_starter_lending_preparation_checklist,
        verbose_name=_("Preparation checklist"),
        help_text=_(
            "Printed with the lending slip. Basic Markdown; “[ ]” becomes a checkbox. "
            "Clear the field and save to get the starter content back."
        ),
    )
    mandatory_regulations = models.ManyToManyField(
        "core.Link",
        through="lending.LendingProfileRegulation",
        related_name="+",
        blank=True,
        verbose_name=_("Mandatory regulations"),
        help_text=_("On the lending slip, the borrower confirms having read them."),
    )
    lent_sheet_template = models.TextField(
        blank=True,
        default=get_starter_lent_sheet_template,
        verbose_name=_("Lending slip template"),
        help_text=_(
            "Django template code; it should extend lending/printout_base.html. Context: record, "
            "lending_profile. The slip body and the checklist are included from lending/includes/, "
            "with sheet_for and pagebreak. Clear the field and save to get the starter content back."
        ),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Lending profile")
        verbose_name_plural = _("Lending profiles")

    def __str__(self):
        return str(self.device_type)

    def clean(self):
        super().clean()
        errors = {}
        for field in ("lent_sheet_template", "lending_preparation_checklist"):
            if match := SCRIPT_RE.search(getattr(self, field)):
                errors[field] = _("Slips may not contain scripts; remove “%(script)s”.") % {"script": match.group()}
        if errors:
            raise ValidationError(errors)
        if self.lent_sheet_template:
            try:
                Template(self.lent_sheet_template)
            except TemplateSyntaxError as e:
                raise ValidationError({"lent_sheet_template": f"Invalid template syntax: {e}"})
