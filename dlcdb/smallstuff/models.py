from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from ..core.models.abstracts import AuditBaseModel


class Thing(AuditBaseModel):
    name = models.CharField(
        max_length=255,
        blank=False,
        unique=True,
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=False,
        unique=True,
    )

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_ou_name',
            ),
            models.UniqueConstraint(
                Lower('slug'),
                name='unique_ou_slug',
            )
        ]

class CurrentlyAssignedThingManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(unassigned_at__isnull=True)


class AssignedThing(models.Model):
    person = models.ForeignKey(
        "core.Person",
        on_delete=models.PROTECT,
    )
    thing = models.ForeignKey(
        "smallstuff.Thing",
        on_delete=models.PROTECT,
    )
    assigned_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_things",
    )
    unassigned_at = models.DateTimeField(
        blank=True,
        null=True,
    )
    unassigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="unassigned_things",
    )

    objects = models.Manager()
    currently_assigned_objects = CurrentlyAssignedThingManager()

    def __str__(self):
        return "{person} ↔ {thing}: {assigned} {unassigned}".format(
            person=self.person,
            thing=self.thing,
            assigned='☑' if self.assigned_at else 'n/a',
            unassigned='☒' if self.unassigned_at else 'n/a',
        )

    def clean(self):
        if self.unassigned_at and not self.assigned_at:
            raise ValidationError(_('Can not be unassigned without being assigned first!'))
        
        if self.assigned_at and self.unassigned_at:
            if self.unassigned_at < self.assigned_at:
                raise ValidationError(_('Unassignment timestamp could not be before assignment timestamp!'))

    class Meta:
        verbose_name = "Assigned thing"
        verbose_name_plural = "Assigned things"
        ordering = ["person__last_name"]
