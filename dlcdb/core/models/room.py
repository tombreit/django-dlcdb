import uuid
from collections import namedtuple
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone, dateformat
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from dlcdb.inventory.utils import uuid2qrcode

from ..storage import OverwriteStorage
from .abstracts import SoftDeleteAuditBaseModel


class Room(SoftDeleteAuditBaseModel):

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name="UUID",
    )
    number = models.CharField(
        max_length=30,
        unique=True,
    )
    nickname = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    description = models.TextField(
        blank=True,
    )
    note = models.TextField(
        blank=True,
    )

    is_auto_return_room = models.BooleanField(
        default=False,
        verbose_name='"Auto return" Raum',
        help_text='Zurückgebene Leihgeräte werden automatisch diesem Raum zugeordnet'
    )
    is_external = models.BooleanField(
        default=False,
        verbose_name='Extern/Verliehen-Raum',
        help_text='Location/Raum, in dem Assets gesammelt werden, die außer Haus sind, z.B. verliehen.',
    )
    qrcode = models.FileField(
        upload_to=f'{settings.QRCODE_DIR}/',
        blank=True,
        null=True,
        storage=OverwriteStorage(),
    )

    class Meta:
        verbose_name = _('Room')
        verbose_name_plural = _('Rooms')
        ordering = ['number', ]

    def __str__(self):
        if not self.nickname:
            return self.number
        return '{} ({})'.format(self.number, self.nickname)

    def save(self, *args, **kwargs):
        """
        Custom save method additionally ensuring the is_auto_return_room=True unique integrity
        and for generating a qrcode.
        """
        if not self.qrcode:
            qrcode = uuid2qrcode(self.uuid, infix=settings.QRCODE_INFIXES.get('room'))
            self.qrcode.save(qrcode.filename, qrcode.fileobj, save=False)
        super().save(*args, **kwargs)
        if self.is_auto_return_room:
            # In case this room is flagged a auto return room, unflag all others.
            # There is only one single auto return room allowed:
            Room.objects.all().exclude(id=self.id).update(is_auto_return_room=False)
        if self.is_external:
            # There is only one single is_external room allowed:
            Room.objects.all().exclude(id=self.id).update(is_external=False)


    def get_active_records(self):
        """
        Returns the active InRoomRecords of this room
        """
        qs = (
            self
            .record_set
            .filter(
                is_active=True,
            )
            .order_by('device__edv_id')
        )
        return qs

    def get_lent_records(self):
        """
        Returns the active lent records associated with this room.
        """
        from . import LentRecord
        return LentRecord.objects.filter(room=self, is_active=True)

    def get_latest_note(self):
        """
        Returns the latest note of the related room and the current inventory.
        """
        return self.room_notes.filter(inventory__is_active=True).order_by('-created_at').first()

    @property
    def get_inventory_status(self):
        """
        Get the inventory status for a given room.
        The inventory status is defined by the count of inroom-devices with a current
        inventory set (see custom model manager above): 
        * outstanding: no devices with current inventory
        * inprogress: some devices with current inventory
        * completed: all devices with current inventory
        """

        inventory_status = namedtuple("inventory_status", [
            "status_str",
            "css_class",
        ])

        if self.room_devices_count == self.room_inventorized_devices_count:
            status_str = 'completed'
            css_class = 'success'
        elif self.room_devices_count == 0:
            status_str = 'completed'
            css_class = 'success'
        elif self.room_devices_count and not self.room_inventorized_devices_count:
            status_str = 'outstanding'
            css_class = 'warning'
        elif self.room_devices_count > self.room_inventorized_devices_count:
            status_str = 'inprogress'
            css_class = 'primary'
        else:
            status_str = 'undefined'
            css_class = 'danger'

        return inventory_status(status_str, css_class)  # ._asdict()


def timestamped_file_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/rooms_reconcile>/<basename>_<timestamp>.<extension>
    now = dateformat.format(timezone.now(), 'Y-m-d_H-i-s')
    filename = Path(filename)
    new_filename = f"{slugify(filename.stem)}_{now}{filename.suffix}"
    return f'rooms_reconcile/{new_filename}'


class RoomReconcile(models.Model):
    file = models.FileField(
        upload_to=timestamped_file_path,
        verbose_name='Datei',
        help_text="Aktuell werden nur Archibus-CSV-Exportdateien unterstützt.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Erstellungsdatum',
    )
    note = models.TextField(
        blank=True,
        verbose_name='Anmerkung',
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = 'Raum-Abgleich'
        verbose_name_plural = 'Raum-Abgleich'

    def __str__(self):
        return f"{Path(self.file.path).name}"
