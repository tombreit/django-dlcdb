# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .. import lifecycle
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

    def apply_lending(self, *, user):
        """
        Saves what a lending screen (the lending frontend or the admin) changed on
        this record, the device's active one, the way the lifecycle wants it:

        - The device is available (INROOM): ``transition_lend`` appends a new LENT
          record with this record's lending fields. This record stays unsaved.
        - A lending with a return date: ``transition_return_lending`` stamps the
          return and moves the device to the auto-return room.
        - A lending without one: a plain save, because editing a lending is not a
          transition.

        Returns the lending: the new LENT record when the device was lent, else
        this record. Any other state raises a ``ValidationError``.
        """
        if self.record_type == Record.INROOM:
            return lifecycle.transition_lend(
                self.device,
                person=self.person,
                room=self.room,
                lent_start_date=self.lent_start_date,
                lent_desired_end_date=self.lent_desired_end_date,
                sync_lent_end_date=self.sync_lent_end_date,
                lent_note=self.lent_note,
                lent_reason=self.lent_reason,
                lent_accessories=self.lent_accessories,
                user=user,
            )
        if self.record_type == Record.LENT and self.lent_end_date:
            lifecycle.transition_return_lending(self, user=user, lent_end_date=self.lent_end_date)
            return self
        if self.record_type == Record.LENT:
            self.stamp_user(user)
            self.save()
            return self
        raise ValidationError(_("Lent state unknown - please report this issue!"))

    def contract_warnings(self):
        """
        The lending screens' warnings about the borrower's HR contract: it has no
        end date, or it ends before the desired return date. They do not stop the
        save.
        """
        contract_end = self.person.udb_contract_planned_checkout
        if not contract_end:
            return [_("Warning: No HR contract end date found for %(person)s!") % {"person": self.person}]
        if self.lent_desired_end_date and self.lent_desired_end_date > contract_end:
            return [_("Warning: Contract ends before the desired return date!")]
        return []

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
