# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models


class Note(models.Model):
    """
    Represents a note. Notes are always bount to a device and optionally bount to an inventory.
    In case a note is bount to an inventory it was created during the inventory process.
    The inventory FK is also the basis to dump the comments.
    """

    text = models.TextField()
    device = models.ForeignKey(
        "core.Device",
        blank=True,
        null=True,
        related_name="device_notes",
        on_delete=models.SET_NULL,
    )
    room = models.ForeignKey(
        "core.Room",
        blank=True,
        null=True,
        related_name="room_notes",
        on_delete=models.SET_NULL,
    )
    inventory = models.ForeignKey(
        "core.Inventory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inventory_notes",
        verbose_name="Inventurzuordnung",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.EmailField(blank=True, editable=False)
    updated_by = models.EmailField(blank=True, editable=False)

    class Meta:
        # TODO: Define unique and unique_together constraints. Eg a
        # device could only have one inventory note per inventory.
        verbose_name = "Notiz"
        verbose_name_plural = "Notizen"
        indexes = [
            models.Index(fields=["created_at", "inventory"]),
        ]

    def __str__(self):
        return "{inventory} - {ts}".format(inventory=self.inventory or "", ts=self.created_at)
