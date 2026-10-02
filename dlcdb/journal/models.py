# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The journal: one append-only log for what happened in DLCDB, modelled on
systemd's journald.

Emitters (imports, syncs, mails, ...) add entries through
``JournalEntry.objects.log()``. An entry is never changed afterwards.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _

from dlcdb.core.utils.helpers import get_denormalized_user


class JournalEntryManager(models.Manager):
    def log(
        self,
        *,
        source,
        event,
        summary,
        body="",
        level=None,
        user=None,
        username=None,
        subject=None,
        tenant=None,
    ):
        """
        Add one entry, the way ``LogEntry.objects.log_actions`` does for the admin.

        ``source`` names the emitter (``"<app_label>.<topic>"``), ``event`` the
        kind of entry within it; filters rely on both, never on the summary text.
        ``level`` defaults to INFO. ``user`` is whoever caused the event.

        ``username`` and ``object_repr`` are snapshots, so an entry still reads
        right after its user or subject is gone. The tenant defaults to the
        subject's tenant; entries without one are visible to every journal viewer.

        Text is data: lazy strings are rendered untranslated, like the admin's
        change messages, so an entry does not depend on who was logged in.
        """
        if level is None:
            level = self.model.Level.INFO
        if username is None:
            username = get_denormalized_user(user).username
        if tenant is None and subject is not None:
            tenant = getattr(subject, "tenant", None)

        with translation.override(None):
            summary = str(summary)
            body = str(body)
            object_repr = str(subject) if subject is not None else ""

        return self.create(
            source=source,
            event=event,
            level=level,
            summary=summary[:255],
            body=body,
            user=user,
            username=username,
            tenant=tenant,
            content_object=subject,
            object_repr=object_repr[:200],
        )


class JournalEntry(models.Model):
    class Level(models.IntegerChoices):
        # Syslog priorities, like journald's PRIORITY=: lower is more severe, so
        # sorting by level sorts by severity and "warning or worse" is level <= 4.
        CRITICAL = 2, _("Critical")
        ERROR = 3, _("Error")
        WARNING = 4, _("Warning")
        SUCCESS = 5, _("Success")  # syslog "notice"
        INFO = 6, _("Info")

    # Not auto_now_add: data migrations copy older logs with their original time.
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Time"),
    )
    source = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("Source"),
    )
    event = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Event"),
    )
    level = models.PositiveSmallIntegerField(
        choices=Level.choices,
        default=Level.INFO,
        verbose_name=_("Level"),
    )
    summary = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Summary"),
    )
    body = models.TextField(
        blank=True,
        verbose_name=_("Details"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("User"),
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Username (denormalized)"),
    )
    tenant = models.ForeignKey(
        "tenants.Tenant",
        # Like Device.tenant. SET_NULL would turn a deleted tenant's entries
        # into tenant-less ones, which every journal viewer sees.
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Tenant"),
    )
    # The optional subject, e.g. the import an entry is about. An integer
    # object_id, unlike the admin's LogEntry: every DLCDB primary key is one.
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("Subject type"),
    )
    object_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Subject ID"),
    )
    content_object = GenericForeignKey("content_type", "object_id")
    object_repr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Subject"),
    )

    objects = JournalEntryManager()

    class Meta:
        ordering = ["-timestamp", "-pk"]
        verbose_name = _("Journal entry")
        verbose_name_plural = _("Journal entries")

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.source}: {self.summary}"
