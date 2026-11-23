# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .abstracts import AuditBaseModel


class Attachment(AuditBaseModel):
    title = models.CharField(
        max_length=255,
        blank=False,
    )
    file = models.FileField(
        blank=False,
        upload_to="attachments/",
    )

    def __str__(self):
        if self.created_at:
            selfstring = f"Attachment: '{self.title}' / Created: '{timezone.localtime(self.created_at):%Y-%m-%d}'"
        else:
            selfstring = f"Attachment: '{self.title}'"

        return selfstring

    class Meta:
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")
        ordering = ["-created_at"]


class Link(AuditBaseModel):
    """A lending regulation: the borrower confirms it on the lending slip, which prints its address."""

    linktext = models.CharField(
        max_length=255,
        blank=False,
        verbose_name=_("Link text"),
    )
    url = models.URLField(
        blank=True,
        verbose_name=_("URL"),
    )
    file = models.FileField(
        blank=True,
        upload_to="links/",
        verbose_name=_("File"),
    )

    @property
    def display_url(self):
        """
        If both url and file are given, only expose the file.
        """
        display_url = self.url

        if self.file:
            scheme = "http" if settings.DEBUG is True else "https"
            domain = f"{scheme}://{Site.objects.get_current().domain}"
            display_url = f"{domain}{self.file.url}"

        return display_url

    def clean(self):
        if not self.url and not self.file:
            raise ValidationError(_("Give a URL or upload a file."))

    def __str__(self):
        return self.linktext

    class Meta:
        verbose_name = _("Lending regulation")
        verbose_name_plural = _("Lending regulations")
        ordering = ["-created_at"]
