from django.conf import settings
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models

from .shortcuts import get_current_tenant


class CurrentTenantManager(models.Manager):
    "Use this to limit objects to those associated with the current site."

    def __init__(self, field_name=None):
        super().__init__()
        self.__field_name = field_name

    def check(self, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(self._check_field_name())
        return errors

    def _check_field_name(self):
        field_name = self._get_field_name()
        try:
            field = self.model._meta.get_field(field_name)
        except FieldDoesNotExist:
            return [
                checks.Error(
                    "CurrentTenantManager could not find a field named '%s'." % field_name,
                    obj=self,
                )
            ]

        if not field.many_to_many and not isinstance(field, (models.ForeignKey)):
            return [
                checks.Error(
                    "CurrentTenantManager cannot use '%s.%s' as it is not a foreign key or a many-to-many field." % (
                        self.model._meta.object_name, field_name
                    ),
                    obj=self,
                )
            ]

        return []

    def _get_field_name(self):
        """ Return self.__field_name or 'site' or 'sites'. """

        if not self.__field_name:
            try:
                self.model._meta.get_field('tenant')
            except FieldDoesNotExist:
                self.__field_name = 'tenants'
            else:
                self.__field_name = 'tenant'
        return self.__field_name

    def get_queryset(self):
        return super().get_queryset().filter(**{self._get_field_name() + '__id': settings.TENANT_ID})



class TenantManager(models.Manager):

    def get_current(self, request=None):
        return self.get_current_tenant(request)
