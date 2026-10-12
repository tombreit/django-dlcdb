# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .record import Record
from .room import Room


class LentRecordQuerySet(models.QuerySet):
    def overdue(self, *, today=None, tolerance_days=0):
        """The overdue lendings among these records, see ``LentRecord.overdue_q``."""
        return self.filter(LentRecord.overdue_q(today=today, tolerance_days=tolerance_days))


class LentRecordManager(models.Manager.from_queryset(LentRecordQuerySet)):
    def get_queryset(self):
        # Lendability is decided by is_lentable alone (see the ``lend``
        # transition in ``dlcdb.core.lifecycle``): a lentable licence can be
        # lent, so its lending must be visible here like any other.
        qs = (
            super()
            .get_queryset()
            .select_related("device")
            .filter(
                is_active=True,
                device__is_lentable=True,
            )
            .exclude(record_type=Record.REMOVED)
            .order_by("-modified_at")
        )

        return qs


class LentRecord(Record):
    objects = LentRecordManager()

    @staticmethod
    def overdue_q(*, today=None, tolerance_days=0):
        """
        What makes a lending overdue, as a ``Q`` for filters and for ``When()`` in
        annotations: a LENT record, not returned yet, whose desired return date
        plus ``tolerance_days`` is on or before ``today``. Without ``today``, it is
        the real today in the current time zone (``timezone.localdate()``, Django's
        today). ``LentRecord.objects.overdue()`` filters by it.

        The tolerance is subtracted from ``today`` rather than added to the return
        date: adding days to a desired return date near 9999-12-31, the last date
        Python knows, would overflow.
        """
        if today is None:
            today = timezone.localdate()
        return Q(
            record_type=Record.LENT,
            lent_end_date__isnull=True,
            lent_desired_end_date__lte=today - timedelta(days=tolerance_days),
        )

    def clean(self):
        if self.device.is_lentable is False:
            # whenever a device is lented, set it to lentable:
            self.device.is_lentable = True
            self.device.save()

        if not self.lent_desired_end_date:
            raise ValidationError({"lent_desired_end_date": _("A desired return date must be set!")})

        if not self.lent_start_date:
            raise ValidationError({"lent_start_date": _("A lending start date must be set!")})

        if self.lent_desired_end_date < self.lent_start_date:
            raise ValidationError(
                {"lent_desired_end_date": _("The desired return date cannot be before the lending start date!")}
            )

        if self.lent_end_date and self.lent_end_date > timezone.localdate():
            raise ValidationError({"lent_end_date": _("The return date cannot be in the future!")})

        if self.lent_end_date and self.lent_end_date < self.lent_start_date:
            raise ValidationError({"lent_end_date": _("The return date cannot be before the lending start date!")})

        if not self.room:
            try:
                extern_room = Room.objects.get(is_external=True)
            except Room.DoesNotExist as e:
                raise ValidationError(_('No extern room set! "%(error)s"') % {"error": e}, code="invalid")
            raise ValidationError(
                {
                    "room": _(
                        "A room must be set! If the location is unclear, the extern room `%(room)s` can be selected."
                    )
                    % {"room": extern_room}
                }
            )

        try:
            Room.objects.get(is_auto_return_room=True)
        except Room.DoesNotExist as e:
            raise ValidationError(_('No auto return room set! "%(error)s"') % {"error": e}, code="invalid")

    def save(self, *args, **kwargs):
        self.record_type = Record.LENT
        super().save(*args, **kwargs)

    class Meta:
        proxy = True
        verbose_name = _("Lending")
        verbose_name_plural = _("Lendings")
