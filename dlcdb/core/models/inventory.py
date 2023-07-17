import json
from collections import namedtuple

from django.db import models, transaction
from django.db.models import Count, IntegerField, Q, OuterRef, Subquery
from django.core.exceptions import ObjectDoesNotExist
from dlcdb.core.utils.helpers import get_denormalized_user

from .room import Room
from .device import Device
from .note import Note
from .record import Record
from .prx_lostrecord import LostRecord


class InventoryQuerySet(models.QuerySet):
    """
    (Experiment with) consolidating most inventory-related querysets.
    """

    def active_inventory(self):
        return self.get(is_active=True)

    _devices_qs = (
        Device
        .objects
        .select_related(
            'manufacturer',
            'active_record',
            'active_record__room',
            'active_record__inventory',
            'device_type',
            'tenant',
        )
    )

    def tenant_unaware_device_objects(self, tenant=None):
        return self._devices_qs

    def tenant_aware_device_objects(self, tenant=None, is_superuser=False):
        qs = Device.objects.none()
        devices_qs = self._devices_qs

        if tenant:
            qs = devices_qs.filter(tenant=tenant)

        if is_superuser:
            qs = devices_qs

        return qs

    def tenant_aware_device_objects_for_room(self, room_pk, tenant=None, is_superuser=False):
        qs = Device.objects.none()

        devices_qs = (
            self._devices_qs
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

    def tenant_aware_room_objects(self, tenant=None):
        qs = (
            Room
            .objects
            .exclude(deleted_at__isnull=False)
        )

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

    @staticmethod
    @transaction.atomic
    def inventorize_uuids_for_room(*, uuids, room_pk, user):
        """
        Main inventorization method: Expects a list of device uuids,
        an inventory status for each uuid and a room and sets an
        appropriate inventory record. 
        """

        try:
            room = Room.objects.get(pk=room_pk)
        except Room.DoesNotExist:
            raise ObjectDoesNotExist("Something went wrong. A room with pk={room_pk} does not exist. Please contact your it staff.")

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
            
            print(f"uuid: {uuid}, state: {state}, device: {device}, active_record: {active_record}")

            new_record = False

            if state == "dev_state_found":
                print("state == 'dev_state_found'")
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

                print("state == 'dev_state_notfound'")

                if all([
                        active_record.record_type == Record.LENT,
                        active_record.room != external_room,
                ]):
                    active_record.room = external_room
                    active_record.save()

                    # Set inventory note
                    # TODO: Fix multiple injections of same note string
                    lent_not_found_msg = f"Lented asset not found in expected location `{active_record.room}`. Please contact lender."
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
