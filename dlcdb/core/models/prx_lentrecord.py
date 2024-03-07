# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .record import Record
from .room import Room


class LentRecordManager(models.Manager):
    def get_queryset(self):
        non_lentable_filter = Q(
            Q(record_type=Record.REMOVED)
            |
            # Q(record_type=Record.LOST) |
            Q(device__is_licence=True)
        )

        qs = (
            super()
            .get_queryset()
            .select_related("device")
            .filter(
                is_active=True,
                device__is_lentable=True,
            )
            .exclude(non_lentable_filter)
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
            raise ValidationError({"lent_desired_end_date": "lent_desired_end_date must be set!"})

        if not self.lent_start_date:
            raise ValidationError({"lent_start_date": "lent_start_date must be set!"})

        if self.lent_desired_end_date < self.lent_start_date:
            raise ValidationError({"lent_desired_end_date": "lent_desired_end_date can not be before lent_start_date!"})

        if self.lent_end_date and self.lent_end_date > datetime.date(now()):
            raise ValidationError({"lent_end_date": "lent_end_date can not be in the future!"})

        if self.lent_end_date and self.lent_end_date < self.lent_start_date:
            raise ValidationError({"lent_end_date": "lent_end_date can not be before lent_start_date!"})

        if self.lent_desired_end_date > datetime.strptime(settings.MAX_FUTURE_LENT_DESIRED_END_DATE, "%Y-%m-%d").date():
            raise ValidationError(
                {
                    "lent_desired_end_date": _(
                        f"The end date (lend_desired_end_date) cannot be after {settings.MAX_FUTURE_LENT_DESIRED_END_DATE}!"
                    )
                }
            )

        if not self.room:
            try:
                extern_room = Room.objects.get(is_external=True)
            except Room.DoesNotExist as e:
                raise ValidationError('No extern room set! "{}"'.format(e), code="invalid")
            raise ValidationError(
                {
                    "room": f"A room must be set! If the location is unclear, the extern room `{extern_room}` room can be selected."
                }
            )

        try:
            Room.objects.get(is_auto_return_room=True)
        except Room.DoesNotExist as e:
            raise ValidationError('No auto return room set! "{}"'.format(e), code="invalid")

    def save(self, *args, **kwargs):
        self.record_type = Record.LENT
        super().save(*args, **kwargs)

    @property
    def get_lent_string_repr(self):
        return f"EDV-ID: {self.device.edv_id}, SAP-ID: {self.device.sap_id}, Manufacturer: {self.device.manufacturer}, Model: {self.device.series}"

    class Meta:
        proxy = True
        verbose_name = _("Lending")
        verbose_name_plural = _("Lendings")
