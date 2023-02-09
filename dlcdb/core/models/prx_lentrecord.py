from datetime import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q, OuterRef, Subquery
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from .record import Record
from .room import Room


class LentRecordManager(models.Manager):

    def get_queryset(self):

        non_lentable_filter = Q(
            Q(record_type=Record.REMOVED) |
            # Q(record_type=Record.LOST) |
            Q(device__is_licence=True)
        )

        qs = (
            super()
            .get_queryset()
            .select_related('device')
            .filter(
                is_active=True,
                device__is_lentable=True,
            )
            .exclude(
                non_lentable_filter
            )
            .order_by('-modified_at')
        )

        return qs

class LentRecord(Record):
    objects = LentRecordManager()

    def clean(self):

        if self.device.is_lentable == False:
            # whenever a device is lented, set it to lentable:
            self.device.is_lentable = True
            self.device.save()

        if not self.lent_desired_end_date:
            raise ValidationError({'lent_desired_end_date': 'lent_desired_end_date must be set!'})

        if not self.lent_start_date:
            raise ValidationError({'lent_start_date': 'lent_start_date must be set!'})

        if self.lent_desired_end_date < self.lent_start_date:
            raise ValidationError({'lent_desired_end_date': 'lent_desired_end_date can not be before lent_start_date!'})

        if self.lent_end_date and self.lent_end_date > datetime.date(now()):
            raise ValidationError({'lent_end_date': 'lent_end_date can not be in the future!'})

        if self.lent_end_date and self.lent_end_date < self.lent_start_date:
            raise ValidationError({'lent_end_date': 'lent_end_date can not be before lent_start_date!'})

        if self.lent_desired_end_date > datetime.strptime(settings.MAX_FUTURE_LENT_DESIRED_END_DATE, '%Y-%m-%d').date():
            raise ValidationError({
                'lent_desired_end_date': _(f'The end date (lend_desired_end_date) cannot be after {settings.MAX_FUTURE_LENT_DESIRED_END_DATE}!')
            })

        try:
            Room.objects.get(is_auto_return_room=True)
        except Room.DoesNotExist as e:
            raise ValidationError('No auto return room set! "{}"'.format(e), code='invalid')

    def save(self, *args, **kwargs):
        self.record_type = Record.LENT
        super().save(*args, **kwargs)

    @property
    def get_lent_string_repr(self):
        return f"EDV-ID: {self.device.edv_id}, SAP-ID: {self.device.sap_id}, Manufacturer: {self.device.manufacturer}, Model: {self.device.series}"

    @staticmethod
    def get_devices(inventory=None, exclude_already_inventorized=False):
        """
        Get devices for lent verification. Used e.d. in case of an inventory:
        Device must be lented and must have a sap_id and do not have a current
        inventory record.
        """
        from ..models import Device, Note

        _exclude_expr = Q()
        if exclude_already_inventorized:
            _exclude_expr = Q(active_record__inventory=inventory)

        devices = (
            Device
            .objects
            # Testing if device has a sap_id and is currently lented
            .exclude(
                Q(sap_id__isnull=True) | 
                Q(sap_id__exact='') |
                Q(active_record__person__isnull=True)
            )
            # Testing if device is currently not already inventorized
            .exclude(
                _exclude_expr
             )
            .annotate(
                inventory_note=Subquery(
                    Note
                    .objects
                    .filter(device=OuterRef('pk'))
                    .filter(inventory=inventory)
                    .order_by('-pk')
                    .values('text')
                )
            )
            .order_by('active_record__person__email')
        )
        return devices

    class Meta:
        proxy = True
        verbose_name = _("Lending")
        verbose_name_plural = _("Lendings")
