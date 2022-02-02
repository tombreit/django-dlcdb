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
