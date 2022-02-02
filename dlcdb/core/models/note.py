from django.db import models

from .device import Device
from .inventory import Inventory
from .room import Room


class Note(models.Model):
    """
    Represents a note. Notes are always bount to a device and optionally bount to an inventory.
    In case a note is bount to an inventory it was created during the inventory process.
    The inventory FK is also the basis to dump the comments.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    device = models.ForeignKey(Device, blank=True, null=True, related_name='device_notes', on_delete=models.SET_NULL)
    room = models.ForeignKey(Room, blank=True, null=True, related_name='room_notes', on_delete=models.SET_NULL)
    inventory = models.ForeignKey(Inventory, null=True, blank=True, verbose_name='Inventurzuordnung', on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Notiz'
        verbose_name_plural = 'Notizen'

    def __str__(self):
        return '{inventory} - {ts}'.format(
            inventory=self.inventory or '',
            ts=self.created_at
        )
