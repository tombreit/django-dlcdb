# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.exceptions import ValidationError
from django.db import models
from django.template import Template, TemplateSyntaxError
from ..core.models.abstracts import SingletonBaseModel


class LendingConfigurationRegulation(models.Model):
    lending_configuration = models.ForeignKey("lending.LendingConfiguration", on_delete=models.CASCADE)
    regulation = models.ForeignKey("core.Link", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("lending_configuration", "regulation")

    def __str__(self):
        return f"LendingConfiguration - {self.regulation.linktext}"


class LendingConfiguration(SingletonBaseModel):
    class OverdueNotificationRecipient(models.TextChoices):
        NONE = "none", "Nobody — no overdue mails"
        LENDER = "lender", "Lender"
        LENDER_AND_IT = "lender_and_it", "Lender, IT in CC"
        IT = "it", "IT only (testdrive: lender mails rerouted to IT)"

    lending_preparation_checklist = models.TextField(
        blank=True, help_text="Basic Markdown supported. '[ ]' converted to checkbox input."
    )
    mandatory_regulations = models.ManyToManyField(
        "core.Link",
        through="lending.LendingConfigurationRegulation",
        related_name="+",
    )
    admin_mark_overdue = models.BooleanField(
        default=True,
        help_text="If checked, the admin listing highlights overdue devices.",
    )
    overdue_notifications_recipient = models.CharField(
        max_length=20,
        choices=OverdueNotificationRecipient.choices,
        default=OverdueNotificationRecipient.LENDER,
        help_text="Who receives the weekly overdue-lending reminder mails. IT = DEFAULT_FROM_EMAIL.",
    )

    def __str__(self):
        return "Lending Configuration"

    class Meta:
        verbose_name = "Lending Configuration"
        verbose_name_plural = "Lending Configuration"


class LendingProfileRegulation(models.Model):
    lending_profile = models.ForeignKey("lending.LendingProfile", on_delete=models.CASCADE)
    regulation = models.ForeignKey("core.Link", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("lending_profile", "regulation")

    def __str__(self):
        return f"LendingProfile ({self.lending_profile.device_type}) - {self.regulation.linktext}"


class LendingProfile(models.Model):
    device_type = models.OneToOneField(
        "core.DeviceType",
        on_delete=models.CASCADE,
        related_name="lending_profile",
        verbose_name="Device Type",
    )
    lending_preparation_checklist = models.TextField(
        blank=True,
        help_text="Basic Markdown supported. '[ ]' converted to checkbox input.",
    )
    mandatory_regulations = models.ManyToManyField(
        "core.Link",
        through="lending.LendingProfileRegulation",
        related_name="+",
        blank=True,
    )
    lent_sheet_template = models.TextField(
        blank=True,
        help_text=(
            "Django template syntax. Should {% extends 'lending/printout_base.html' %}. "
            "Available context: record, lending_profile, sheet_for, pagebreak."
        ),
    )

    class Meta:
        verbose_name = "Lending Profile"
        verbose_name_plural = "Lending Profiles"

    def __str__(self):
        return f"Lending Profile: {self.device_type}"

    def clean(self):
        super().clean()
        if self.lent_sheet_template:
            try:
                Template(self.lent_sheet_template)
            except TemplateSyntaxError as e:
                raise ValidationError({"lent_sheet_template": f"Invalid template syntax: {e}"})
