# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import json
from collections import namedtuple

from django.db import models, transaction
from django.db.models import Count, Q, OuterRef, Subquery, Exists
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from dlcdb.core.utils.helpers import get_denormalized_user
from dlcdb.inventory.utils import update_inventory_note

from .room import Room
from .device import Device
from .note import Note
from .record import Record
from .prx_lostrecord import LostRecord


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

    def tenant_aware_device_objects(self, tenant=None, is_superuser=False):
        qs = Device.objects.none()
        devices_qs = self._devices_qs()

        if tenant:
            qs = devices_qs.filter(tenant=tenant)

        if is_superuser:
            qs = devices_qs

        return qs

    def tenant_aware_device_objects_for_room(self, room_pk, tenant=None, is_superuser=False):
        qs = Device.objects.none()

        devices_qs = (
            self._devices_qs()
            .filter(
                active_record__is_active=True,
                active_record__room__pk=room_pk,
                active_record__device__deleted_at__isnull=True,
            )
            .annotate(has_inventory_note=Exists(self._current_inventory_device_note()))
            .annotate(already_inventorized=Exists(self._current_inventory_records()))
        )

        if tenant:
            qs = devices_qs.filter(tenant=tenant)

        if is_superuser:
            qs = devices_qs

        return qs

    def inventory_relevant_devices(self, tenant=None, is_superuser=False):
        return (
            Inventory.objects.tenant_aware_device_objects(tenant=tenant, is_superuser=is_superuser)
            .exclude(active_record__record_type=Record.REMOVED)
            .exclude(sap_id__isnull=True)
            .exclude(sap_id__exact="")
            .annotate(already_inventorized=Exists(self._current_inventory_records()))
        ).distinct()

    def tenant_aware_room_objects(self, tenant=None):
        current_inventory_room_note = Note.objects.filter(
            room=OuterRef("pk"),
            inventory=self.get(is_active=True),
        )

        qs = Room.objects.exclude(deleted_at__isnull=False).annotate(
            has_inventory_note=Exists(current_inventory_room_note)
        )

        # Some inventory stats done by the database.
        if tenant:
            qs = qs.annotate(
                room_devices_count=Count(
                    "record",
                    filter=Q(
                        record__is_active=True,
                        record__device__deleted_at__isnull=True,
                        record__device__tenant=tenant,
                    ),
                ),
                room_inventorized_devices_count=Count(
                    "record",
                    filter=Q(
                        Q((Q(record__record_type=Record.INROOM) | Q(record__record_type=Record.LENT))),
                        record__device__deleted_at__isnull=True,
                        record__inventory__is_active=True,
                        record__device__tenant=tenant,
                    ),
                ),
                # room_inventorized_devices_count=Sum(
                #     Case(
                #         When(
                #             record__in=inventorized_records_in_room,
                #             # record__is_active=True,
                #             then=1
                #         ),
                #         default=0,
                #         output_field=models.IntegerField()
                #     )
                # )
            )
        else:
            qs = qs.annotate(
                room_devices_count=Count(
                    "record",
                    filter=Q(
                        record__is_active=True,
                        record__device__deleted_at__isnull=True,
                    ),
                ),
                room_inventorized_devices_count=Count(
                    "record",
                    filter=Q(
                        Q((Q(record__record_type=Record.INROOM) | Q(record__record_type=Record.LENT))),
                        record__device__deleted_at__isnull=True,
                        record__inventory__is_active=True,
                    ),
                ),
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


class Inventory(models.Model):
    """
    Represents an inventory.
    An inventory represents one real world inventory. E.g. there is may be an inventory for
    december 2018 and an inventory for january 2019.
    """

    name = models.CharField(max_length=255, verbose_name="Name")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name="Aktiv")

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

    def get_inventory_progress(self, tenant=None, is_superuser=False):
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

        _inventory_relevant_devices = Inventory.objects.inventory_relevant_devices(
            tenant=tenant, is_superuser=is_superuser
        )

        inventory_relevant_devices_inventorized_count = (
            _inventory_relevant_devices.filter(already_inventorized=True)
        ).count()
        inventory_relevant_devices_count = _inventory_relevant_devices.count()

        done_percent = 0
        done_percent = (inventory_relevant_devices_inventorized_count * 100) / inventory_relevant_devices_count
        done_percent = int(round(done_percent, 0))

        return inventory_progress(
            done_percent, inventory_relevant_devices_count, inventory_relevant_devices_inventorized_count
        )

    @staticmethod
    @transaction.atomic
    def inventorize_uuids_for_room(*, uuids, room_pk, user):
        """
        Main inventorization method: Expects a list of device uuids,
        an inventory status for each uuid and a room and sets an
        appropriate inventory record.
        """

        # print(f"inventorize_uuids_for_room {uuids=}, {room_pk=}, {user=}")

        try:
            room = Room.objects.get(pk=room_pk)
        except Room.DoesNotExist:
            raise ObjectDoesNotExist(
                "Something went wrong. A room with pk={room_pk} does not exist. Please contact your it staff."
            )

        try:
            external_room = Room.objects.get(is_external=True)
        except Room.DoesNotExist:
            raise ObjectDoesNotExist("No room is flagged with 'is_external'. Please contact your it staff.")

        current_inventory = Inventory.objects.active_inventory()
        user, username = get_denormalized_user(user)
        uuids_states_dict = json.loads(uuids)

        for uuid, state in uuids_states_dict.items():
            try:
                device = Device.objects.get(uuid=uuid)
            except Device.DoesNotExist as does_not_exist:
                raise ObjectDoesNotExist(f"No device for uuid {uuid}! {does_not_exist}")

            active_record = device.active_record

            # print(f"uuid: {uuid}, state: {state}, device: {device}, active_record: {active_record}")

            new_record = False

            # TODO: Refactor these inventory actions to be part of the Inventory
            # model

            if state == "dev_state_found":
                new_record = active_record
                new_record.room = room
                new_record.inventory = current_inventory
                new_record.user = user
                new_record.username = username

                # As we copied a previous record, we need to do some
                # cleanup in fields which doest not match the new
                # record type:
                if new_record.record_type == Record.LOST:
                    new_record.record_type = Record.INROOM
                    new_record.note = ""
                elif new_record.record_type == Record.REMOVED:
                    new_record.record_type = Record.INROOM
                    new_record.disposition_state = ""
                    new_record.removed_info = ""
                    new_record.note = ""
                    new_record.removed_date = None

            elif state == "dev_state_notfound":
                # If an expected device is not found in a given room, we need
                # to check if it is currently lended. When lended, we do not
                # set this device as "not found", but instead move it to an
                # "external room".

                if all(
                    [
                        active_record.record_type == Record.LENT,
                        active_record.room != external_room,
                    ]
                ):
                    active_record.room = external_room
                    active_record.save()

                    # Set inventory note
                    # TODO: Fix multiple injections of same note string
                    lent_not_found_msg = f"Lented asset not found in expected location `{active_record.room}`."
                    note_obj, note_obj_created = Note.objects.get_or_create(
                        inventory=current_inventory,
                        device=active_record.device,
                        room=external_room,
                    )
                    note_obj.text = f"{note_obj.text} *** {lent_not_found_msg}"
                    note_obj.save()
                else:
                    new_record = LostRecord(
                        device=device,
                        inventory=current_inventory,
                        user=user,
                        username=username,
                    )

            elif state == "dev_state_unknown":
                # This could happen if a device is added to a room via add_device
                # but that device is not marked as "found" or "not found".
                # That device should be added to current room, but without
                # an inventory record.
                # Or if an already inventorized device is marked as "unknown", for
                # whatever reason.

                new_record = active_record
                new_record.room = room
                new_record.user = user
                new_record.username = username
                new_record_note = "Marked as 'unknown state' during inventory."

                # How to handle devices which already have an inventory record
                # but are marked as "unknown" during inventory?
                # Keeping the current inventory value vs. removing the inventory
                # As we count a device as inventorized if we have any record with
                # a inventory stamp for the current inventory, the UI will still
                # show this device as inventorized.
                new_record.inventory = None

                already_inventorized_records = device.get_current_inventory_records
                if already_inventorized_records:
                    # The device was already inventorized, but is now marked as "unknown".
                    # This could happen if a user previously falsely marked a device as "inventorized"
                    # and now wants to remove this inventory stamp.

                    # Not using batch update mode here, as we need to be sure that
                    # the models save() method is called.
                    # already_inventorized_records.update(inventory=None)
                    for _record in already_inventorized_records:
                        _record.inventory = None
                        _record.save()

                    # ...and add an audit trail inventory note
                    msg = f"Device marked as 'unknown state' during inventory by {user}. Removed existing inventory stamp."
                    _inventory_note_obj = update_inventory_note(
                        inventory=current_inventory,
                        device=device,
                        msg=msg,
                    )

                # As we copied a previous record, we need to do some
                # cleanup in fields which doest not match the new
                # record type:
                if new_record.record_type == Record.LOST:
                    new_record.record_type = Record.INROOM
                    new_record.note = new_record_note
                elif new_record.record_type == Record.REMOVED:
                    new_record.record_type = Record.INROOM
                    new_record.disposition_state = ""
                    new_record.removed_info = ""
                    new_record.note = new_record_note
                    new_record.removed_date = None
                elif new_record.record_type == Record.INROOM:
                    new_record.note = new_record_note

            else:
                msg = f"This should never happen: given state `{state}` not recognized! Raising 500."
                print(msg)
                raise RuntimeError(msg)

            if new_record:
                # Copying model instances
                # https://docs.djangoproject.com/en/4.2/topics/db/queries/#copying-model-instances
                new_record.pk = None
                new_record._state.adding = True
                new_record.save()
