# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

# auto_now_add and auto_now issue two separate timezone.now() calls when a row is
# inserted, so a freshly created object's timestamps differ by microseconds
# rather than being equal. Anything inside this window counts as "never touched
# since it was created".
UNMODIFIED_TOLERANCE = datetime.timedelta(seconds=1)


class AuditBaseModel(models.Model):
    user = models.ForeignKey(
        # get_user_model(),
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Username (denormalized)"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
    )
    modified_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Modified"),
    )

    class Meta:
        abstract = True

    @property
    def is_unmodified(self):
        """
        True when this object has not been edited since it was created.

        Lets a list column show both timestamps without printing the same value
        twice for a row nobody has touched yet.
        """
        if not self.created_at or not self.modified_at:
            # Unsaved instance: neither auto stamp has been written yet.
            return False
        return self.modified_at - self.created_at < UNMODIFIED_TOLERANCE


class SoftDeleteAuditBaseModelQuerySet(models.QuerySet):
    """
    Prevents objects from being hard-deleted. Instead, sets the
    ``deleted_at``, effectively soft-deleting the object.
    """

    def delete(self):
        for obj in self:
            obj.deleted_at = now()
            obj.save()

    def hard_delete(self):
        return super().delete()

    def not_deleted_objects(self):
        return self.filter(deleted_at__isnull=True)

    def with_deleted_objects(self):
        return self.filter()

    def only_deleted_objects(self):
        return self.filter(deleted_at__isnull=False)


class WithDeletedObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteAuditBaseModelQuerySet(self.model, using=self._db).with_deleted_objects()


class NotDeletedObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteAuditBaseModelQuerySet(self.model, using=self._db).not_deleted_objects()


class OnlyDeletedObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteAuditBaseModelQuerySet(self.model, using=self._db).only_deleted_objects()


class SoftDeleteAuditBaseModel(AuditBaseModel):
    """
    SoftDeleteAuditBaseModel could be used for Device, Room, DeviceType etc.
    Currently not suitable for Record instances.
    """

    deleted_at = models.DateTimeField(
        editable=False,
        null=True,
    )
    deleted_by = models.ForeignKey(
        # get_user_model(),
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = NotDeletedObjectsManager()
    with_softdeleted_objects = WithDeletedObjectsManager()
    only_softdeleted_objects = OnlyDeletedObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        if self.pk is None:
            raise ValueError(
                "%s object can't be deleted because its %s attribute is set "
                "to None." % (self._meta.object_name, self._meta.pk.attname)
            )
        self.deleted_at = now()
        self.save()

    def hard_delete(self):
        super().delete()


class SingletonBaseModel(models.Model):
    def clean(self):
        if self.__class__.objects.exclude(id=self.id).exists():
            raise ValidationError(
                "There can be only one instance for this object. Instead of add a new instance, edit the already existing object."
            )

    # This approach does overwrite the first instance with a second
    # instance.
    # def save(self, *args, **kwargs):
    #     self.pk = 1
    #     super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     return super().save(*args, **kwargs)

    # def delete(self, *args, **kwargs):
    #     pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        abstract = True
