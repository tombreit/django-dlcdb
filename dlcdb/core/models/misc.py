from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.sites.models import Site

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
            selfstring = f"Attachment: '{self.title}' / Created: '{self.created_at:%Y-%m-%d}'"
        else:
            selfstring = f"Attachment: '{self.title}'"

        return selfstring

    class Meta:
        verbose_name = "Attachment"
        verbose_name_plural = "Attachments"
        ordering = ["-created_at"]


class Link(AuditBaseModel):
    linktext = models.CharField(
        max_length=255,
        blank=False,
    )
    url = models.URLField(
        blank=True,
    )
    file = models.FileField(
        blank=True,
        upload_to="links/",
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
        # Check if both fields are empty
        if not self.url and not self.file:
            raise ValidationError('At least one of the fields "url" or "file" must be filled.')

    def __str__(self):
        return f"Link: '{self.linktext}'"

    class Meta:
        verbose_name = "Link"
        verbose_name_plural = "Links"
        ordering = ["-created_at"]
