# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from collections import namedtuple

from django.db import models
from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils.translation import gettext_lazy as _

from .device import Device
from .note import Note
from .record import Record
from .room import Room


class InventoryQuerySet(models.QuerySet):
    """
    (Experiment with) consolidating most inventory-related querysets.
    TODO: Refactor to chainable querysets, e.g. with "for_room()", "for_tenant()"
    FIXME: Implement a reliable and performant way to get already inventorized
    devices for rooms.
    TODO: underscore methods could possibly replaced by Subqueries
    """

    def _devices_qs(self):
        return Device.objects.select_related(
            "manufacturer",
            "active_record",
            "active_record__room",
            "active_record__inventory",
            "device_type",
            "tenant",
        )

    def _current_inventory_records(self):
        return Record.objects.filter(
            device=OuterRef("pk"),
            inventory__is_active=True,
            # We don't care if the iventory stamp is on the latest active
            # record, we regard a device as inventorized, if we have any
            # record with a inventory stamp for the current inventory:
            # is_active=True,
        )

    def _current_inventory_device_note(self):
        return Note.objects.filter(
            device=OuterRef("pk"),
            inventory__is_active=True,
        )

    def active_inventory(self):
        try:
            inventory = self.get(is_active=True)
        except Inventory.DoesNotExist:
            inventory = None

        return inventory

    def tenant_unaware_device_objects(self):
        return self._devices_qs().annotate(has_inventory_note=Exists(self._current_inventory_device_note()))

    def tenant_aware_device_objects(self, *, tenants):
        return self._devices_qs().filter(tenant__in=tenants)

    def tenant_aware_device_objects_for_room(self, room_pk, *, tenants):
        return (
            self._devices_qs()
            .filter(
                active_record__is_active=True,
                active_record__room__pk=room_pk,
                active_record__device__deleted_at__isnull=True,
                tenant__in=tenants,
            )
            .annotate(has_inventory_note=Exists(self._current_inventory_device_note()))
            .annotate(already_inventorized=Exists(self._current_inventory_records()))
        )

    def inventory_relevant_devices(self, *, tenants):
        device_search_tenant_aware = self.active_inventory().device_search_tenant_aware

        if device_search_tenant_aware:
            qs = Inventory.objects.tenant_aware_device_objects(tenants=tenants)
        else:
            qs = Inventory.objects.tenant_unaware_device_objects()

        return (
            qs.exclude(active_record__record_type=Record.REMOVED)
            .exclude(sap_id__isnull=True)
            .exclude(sap_id__exact="")
            .annotate(already_inventorized=Exists(self._current_inventory_records()))
        ).distinct()

    def tenant_aware_room_objects(self, *, tenants):
        current_inventory_room_note = Note.objects.filter(
            room=OuterRef("pk"),
            inventory=self.get(is_active=True),
        )

        qs = Room.objects.exclude(deleted_at__isnull=False).annotate(
            has_inventory_note=Exists(current_inventory_room_note)
        )

        # The room's devices that are counted in the current inventory. A device
        # counts once, if any of its records carries the current stamp: what the
        # room's device list (``already_inventorized``) and the overall progress
        # count too. Counting the room's stamped records instead counted a device
        # scanned twice twice, and kept counting one that had moved on.
        counted_devices = (
            Device.objects.filter(
                active_record__room=OuterRef("pk"),
                active_record__is_active=True,
                deleted_at__isnull=True,
                tenant__in=tenants,
                record__inventory__is_active=True,
            )
            .order_by()
            .values("active_record__room")
            .annotate(count=Count("pk", distinct=True))
            .values("count")
        )

        # Some inventory stats done by the database. Rooms are shared by all
        # tenants, only their device counts are tenant-scoped.
        qs = qs.annotate(
            room_devices_count=Count(
                "record",
                filter=Q(
                    record__is_active=True,
                    record__device__deleted_at__isnull=True,
                    record__device__tenant__in=tenants,
                ),
            ),
            room_inventorized_devices_count=Coalesce(Subquery(counted_devices, output_field=IntegerField()), 0),
        )

        return qs.order_by("number")

    def lent_devices(self, exclude_already_inventorized=False):
        """
        Get devices for lent verification. Used in case of an inventory:
        Device must be lented and must have a sap_id and do not have a current
        inventory record.
        """

        _exclude_expr = Q()
        if exclude_already_inventorized:
            # _exclude_expr = Q(active_record__inventory=self.active_inventory())
            # If any record has an current inventory stamp, count this device as
            # inventorized and exclude it from the mailing.
            _exclude_expr = Q(already_inventorized=True)

        devices = (
            Device.objects
            # Testing if device has a sap_id and is currently lented
            .exclude(Q(sap_id__isnull=True) | Q(sap_id__exact="") | Q(active_record__person__isnull=True))
            .annotate(already_inventorized=Exists(self._current_inventory_records()))
            # Testing if device is currently not already inventorized
            .exclude(_exclude_expr)
            .annotate(
                inventory_note=Subquery(
                    Note.objects.filter(device=OuterRef("pk"))
                    .filter(inventory=self.active_inventory())
                    .order_by("-pk")
                    .values("text")
                )
            )
            .order_by("active_record__person__email")
        )
        return devices


def get_active_inventory(request):
    """
    Per-request memoized Inventory.objects.active_inventory(): context
    processors and views handling the same request share one query.
    """
    if not hasattr(request, "_active_inventory"):
        request._active_inventory = Inventory.objects.active_inventory()
    return request._active_inventory


class Inventory(models.Model):
    """
    Represents an inventory.
    An inventory represents one real world inventory. E.g. there is may be an inventory for
    december 2018 and an inventory for january 2019.
    """

    name = models.CharField(max_length=255, verbose_name="Name")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name="Aktiv")
    device_search_tenant_aware = models.BooleanField(
        default=True,
        verbose_name=_("Device search tenant aware"),
        help_text=_("If set, the device search will only return devices of the user's tenants."),
    )

    # started_on = models.DateField(
    #     null=True,
    #     blank=True,
    #     help_text=_("Date this inventory startet. Some aspects of the system behave differently when it is in an inventory time window."),
    # )
    # completed_on = models.DateField(
    #     null=True,
    #     blank=True,
    #     help_text=_("Date this inventory startet. Some aspects of the system behave differently when it is in an inventory time window."),
    # )

    objects = InventoryQuerySet.as_manager()

    class Meta:
        verbose_name = _("Inventory")
        verbose_name_plural = _("Inventories")
        permissions = [
            ("can_inventorize", "Can inventorize devices"),
        ]

    def __str__(self):
        return f"{_('Inventory')} {self.name}"

    def save(self, *args, **kw):
        """
        Whenenver an inventory is saved as active all other inventories are saved as inactive.
        There is only one active inventory.
        """
        if self.is_active:
            # deactivate all other inventories in case this inventory was set active.
            Inventory.objects.exclude(id=self.id).update(is_active=False)

        super().save(*args, **kw)

    def get_inventory_progress(self, *, tenants):
        """
        Get status for inventory, e.g. "5 from 10 assets already inventorized".
        """

        inventory_progress = namedtuple(
            "inventory_progress",
            [
                "done_percent",
                "all_devices_count",
                "inventorized_devices_count",
            ],
        )

        _inventory_relevant_devices = Inventory.objects.inventory_relevant_devices(tenants=tenants)

        inventory_relevant_devices_inventorized_count = (
            _inventory_relevant_devices.filter(already_inventorized=True)
        ).count()
        inventory_relevant_devices_count = _inventory_relevant_devices.count()

        done_percent = 0
        if inventory_relevant_devices_count:
            done_percent = (inventory_relevant_devices_inventorized_count * 100) / inventory_relevant_devices_count
            done_percent = int(round(done_percent, 0))

        return inventory_progress(
            done_percent, inventory_relevant_devices_count, inventory_relevant_devices_inventorized_count
        )
