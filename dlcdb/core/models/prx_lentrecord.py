# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .record import Record
from .room import Room


class LentRecordManager(models.Manager):
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

        if self.lent_end_date and self.lent_end_date > datetime.date(now()):
            raise ValidationError({"lent_end_date": _("The return date cannot be in the future!")})

        if self.lent_end_date and self.lent_end_date < self.lent_start_date:
            raise ValidationError({"lent_end_date": _("The return date cannot be before the lending start date!")})

        if self.lent_desired_end_date > datetime.strptime(settings.MAX_FUTURE_LENT_DESIRED_END_DATE, "%Y-%m-%d").date():
            # Interpolate *outside* gettext: an f-string inside _() cannot be
            # extracted by makemessages and its msgid would vary at runtime.
            raise ValidationError(
                {
                    "lent_desired_end_date": _("The desired return date cannot be after %(max_date)s!")
                    % {"max_date": settings.MAX_FUTURE_LENT_DESIRED_END_DATE}
                }
            )

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
