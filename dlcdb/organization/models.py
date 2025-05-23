# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models

from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

from dlcdb.core.models.abstracts import SingletonBaseModel


def validate_logo_image_file_extension(value):
    valid_extensions = ["svg"]
    return FileExtensionValidator(allowed_extensions=valid_extensions)(value)


def validate_favicon_file_extension(value):
    valid_extensions = ["ico"]
    return FileExtensionValidator(allowed_extensions=valid_extensions)(value)


class Branding(SingletonBaseModel):
    organization_name_en = models.CharField(
        max_length=255,
        blank=False,
        verbose_name="Organization Name (EN)",
        default=_("A Company that Makes Everything"),
        help_text=_("Company, institute, site name (english version)."),
    )
    organization_name_de = models.CharField(
        max_length=255,
        blank=False,
        verbose_name="Organization Name (DE)",
        default=_("A Company that Makes Everything"),
        help_text=_("Company, institute, site name (german version)."),
    )
    organization_abbr = models.CharField(
        max_length=255,
        blank=False,
        verbose_name="Abbreviation",
        default="DLCDB",
        help_text=_("Company, institute, site abbreviation."),
    )
    organization_street = models.CharField(
        max_length=255, blank=True, help_text="Street and house number. Used in printouts etc."
    )
    organization_zip_code = models.CharField(
        max_length=255, blank=True, verbose_name="Organization ZIP Code", help_text="Used in printouts etc."
    )
    organization_city = models.CharField(max_length=255, blank=True, help_text="Used in printouts etc.")
    organization_url = models.URLField(blank=True, verbose_name="Organization URL", help_text="Used in printouts etc.")
    organization_logo_white = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name="Logo file (white)",
        help_text=_(
            "Logo file. SVG, white foreground, transparent background. Used in the main navigation bar/site header."
        ),
    )
    organization_logo_black = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name="Logo file (black)",
        help_text=_("Logo file. SVG, black foreground, transparent background. Used in PDF printouts."),
    )
    organization_figurative_mark = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name="Figurative Mark/Bildmarke",
        help_text="Bildmarke, quasi Logo ohne Wortmarke.",
    )
    organization_favicon = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_favicon_file_extension],
        verbose_name="Favicon file",
    )

    organization_it_dept_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="IT Department Name",
        help_text="Wording for the IT department. Used in printouts etc.",
    )
    organization_it_dept_phone = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="IT Department Phone",
    )
    organization_it_dept_email = models.EmailField(
        blank=True,
        verbose_name="IT Department Email",
    )

    licenses_logo = models.FileField(
        null=True,
        blank=True,
        upload_to="branding/",
        validators=[validate_logo_image_file_extension],
        verbose_name="Logo file for Licenses component",
    )

    room_plan = models.FileField(
        blank=True,
        null=True,
        upload_to="branding/",
    )

    documentation_url = models.URLField(
        blank=True,
        default="https://dlcdb.pages.gwdg.de/django-dlcdb/",
        help_text="If you host the documentation on your own, provide the URL here.",
    )

    def __str__(self):
        return f"Branding for {self.organization_name_en or 'n/a'}"

    class Meta:
        verbose_name = "Branding"
        verbose_name_plural = "Branding"
