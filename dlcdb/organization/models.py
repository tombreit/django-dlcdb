# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models.abstracts import SingletonBaseModel


def validate_logo_image_file_extension(value):
    valid_extensions = ["svg"]
    return FileExtensionValidator(allowed_extensions=valid_extensions)(value)


def validate_favicon_file_extension(value):
    """model field removed, validator kept to keep history of migrations intact"""
    valid_extensions = ["ico"]
    return FileExtensionValidator(allowed_extensions=valid_extensions)(value)


class Branding(SingletonBaseModel):
    organization_name_en = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Organization name (English)"),
        default=_("A Company that Makes Everything"),
        help_text=_("Company, institute, site name (english version)."),
    )
    organization_name_de = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Organization name (German)"),
        default=_("A Company that Makes Everything"),
        help_text=_("Company, institute, site name (german version)."),
    )
    organization_abbr = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Abbreviation"),
        default="DLCDB",
        help_text=_("Company, institute, site abbreviation."),
    )
    organization_street = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Street"),
        help_text=_("Street and house number. Used in printouts."),
    )
    organization_zip_code = models.CharField(
        max_length=255, blank=True, verbose_name=_("ZIP code"), help_text=_("Used in printouts.")
    )
    organization_city = models.CharField(
        max_length=255, blank=True, verbose_name=_("City"), help_text=_("Used in printouts.")
    )
    organization_url = models.URLField(blank=True, verbose_name=_("Website"), help_text=_("Used in printouts."))
    organization_logo_black = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name=_("Logo"),
        help_text=_("Logo file. SVG, black foreground, transparent background. Used in PDF printouts."),
    )
    organization_figurative_mark = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name=_("Figurative mark"),
        help_text=_("The logo without its lettering. SVG. Used in printouts."),
    )

    organization_it_dept_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("IT department name"),
        help_text=_("Wording for the IT department. Used in printouts."),
    )
    organization_it_dept_phone = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("IT department phone"),
    )
    organization_it_dept_email = models.EmailField(
        blank=True,
        verbose_name=_("IT department email"),
        help_text=_("Used in printouts and mails, and for overdue reminders of tenants without a contact email."),
    )

    room_plan = models.FileField(
        blank=True,
        null=True,
        upload_to="branding/",
        verbose_name=_("Room plan"),
        help_text=_("A file, e.g. a PDF, linked from the room lists."),
    )

    documentation_url = models.URLField(
        blank=True,
        default="https://tombreit.github.io/django-dlcdb/",
        verbose_name=_("Documentation URL"),
        help_text=_("If you host the documentation on your own, provide the URL here."),
    )

    def __str__(self):
        return f"Branding for {self.organization_name_en or 'n/a'}"

    class Meta:
        verbose_name = _("Organization")
        verbose_name_plural = _("Organization")
