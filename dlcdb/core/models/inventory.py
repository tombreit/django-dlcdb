from collections import namedtuple
from django.db import models


class Inventory(models.Model):
    """
    Represents an inventory.
    An inventory represents one real world inventory. E.g. there is may be an inventory for
    december 2018 and an inventory for january 2019.
    """
    name = models.CharField(max_length=255, verbose_name='Name')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    is_active = models.BooleanField(default=False, verbose_name='Aktiv')

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
