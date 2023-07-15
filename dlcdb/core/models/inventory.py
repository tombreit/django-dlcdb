from collections import namedtuple
from django.db import models
from django.db.models import Count, IntegerField, Q, OuterRef, Subquery

from .room import Room
from .device import Device
from .note import Note


class InventoryQuerySet(models.QuerySet):
    """
    (Experiment with) consolidating most inventory-related querysets.
    """

    def active_inventory(self):
        return self.get(is_active=True)

    def tenant_unaware_device_objects(self, tenant=None):
        return (
            Device
            .objects
            .select_related(
                'manufacturer',
                'active_record',
                'active_record__room',
                'active_record__inventory',
                'device_type',
            )
        )

    def devices_for_room(self, room_pk, tenant=None, is_superuser=False):
        qs = Device.objects.none()
        
        devices_qs = (
            Device
            .objects
            .select_related('active_record')
            .filter(
                active_record__is_active=True,
                active_record__room__pk=room_pk,
                active_record__device__deleted_at__isnull=True,
            )
        )

        if tenant:
            qs = devices_qs.filter(tenant=tenant)

        if is_superuser:
            qs = devices_qs

        return qs


    def tenant_aware_devices_for_room(self, room_pk, is_superuser, tenant):
        # By default do not expose any devices
        devices_qs = Device.objects.none()

        # Allow all rooms, even soft deleted rooms
        # room = Room.with_softdeleted_objects.get(pk=room_pk)
        room = Room.objects.get(pk=room_pk)
        base_qs = room.get_devices()

        if tenant:
            devices_qs = base_qs.filter(tenant=tenant)

        if is_superuser:
            devices_qs = base_qs

        return devices_qs.order_by('-modified_at')


    def tenant_aware_room_objects(self, tenant=None):
        qs = Room.objects.exclude(deleted_at__isnull=False)

        if tenant:
            qs = (
                qs
                .annotate(
                    room_devices_count=Count('pk', filter=Q(
                        record__is_active=True,
                        record__device__deleted_at__isnull=True,
                        record__device__tenant=tenant,
                    ), output_field=IntegerField()),
                    room_inventorized_devices_count=Count('pk', filter=Q(
                        record__is_active=True,
                        record__inventory__is_active=True,
                        record__device__deleted_at__isnull=True,
                        record__device__tenant=tenant,
                    ), output_field=IntegerField()),
                )
            )
        else:
            qs = (
                qs
                .annotate(
                    room_devices_count=Count('pk', filter=Q(
                        record__is_active=True,
                        record__device__deleted_at__isnull=True,
                    ), output_field=IntegerField()),
                    room_inventorized_devices_count=Count('pk', filter=Q(
                        record__is_active=True,
                        record__inventory__is_active=True,
                        record__device__deleted_at__isnull=True,
                    ), output_field=IntegerField()),
                )
            )

        return qs.order_by("number")

    def lent_devices(self, exclude_already_inventorized=False):
        """
        Get devices for lent verification. Used e.d. in case of an inventory:
        Device must be lented and must have a sap_id and do not have a current
        inventory record.
        """

        current_inventory = self.get(is_active=True)

        _exclude_expr = Q()
        if exclude_already_inventorized:
            _exclude_expr = Q(active_record__inventory=current_inventory)

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
                    .filter(inventory=current_inventory)
                    .order_by('-pk')
                    .values('text')
                )
            )
            .order_by('active_record__person__email')
        )
        return devices



class Inventory(models.Model):
    """
    Represents an inventory.
    An inventory represents one real world inventory. E.g. there is may be an inventory for
    december 2018 and an inventory for january 2019.
    """
    name = models.CharField(max_length=255, verbose_name='Name')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name='Aktiv')

    objects = InventoryQuerySet.as_manager()

    class Meta:
        verbose_name = 'Inventur'
        verbose_name_plural = 'Inventuren'

    def __str__(self):
        return 'Inventur %s' % self.name

    def save(self, *args, **kw):
        """
        Whenenver an inventory is saved as active all other inventories are saved as inactive.
        There is only one active inventory.
        """
        if self.is_active:
            # deactivate all other inventories in case this inventory was set active.
            Inventory.objects.exclude(id=self.id).update(is_active=False)

        super().save(*args, **kw)


    def get_inventory_progress(self, tenant=None):
        """
        Get status for inventory, e.g. "5 from 10 assets already inventorized".
        TODO: Should be a method of the Inventory class.
        """
        from dlcdb.core.models import Record

        inventory_progress = namedtuple(
            "inventory_progress",
            [
                "done_percent",
                "all_devices_count",
                "inventorized_devices_count",
            ],
        )

        done_percent = 0
        all_devices = Record.objects.active_records().exclude(record_type=Record.REMOVED)

        if tenant:
            all_devices = all_devices.filter(device__tenant=tenant)

        inventorized_devices_count = all_devices.filter(inventory=self).count()
        all_devices_count = all_devices.count()

        done_percent = (inventorized_devices_count * 100) / all_devices_count
        done_percent = int(round(done_percent, 0))

        return inventory_progress(done_percent, all_devices_count, inventorized_devices_count)
