# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Field-level helpers for CSV device imports: resolving foreign keys and
parsing/normalizing scalar values from CSV cells.
"""

import string
from datetime import datetime

from django.apps import apps
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.timezone import make_aware


def set_datetime_field(value):
    result_value = None

    if value:
        try:
            result_value = datetime.strptime(value, "%Y-%m-%d")
            result_value = make_aware(result_value)
        except ValueError as value_error:
            raise ValueError(f"{value_error}: Incorrect date format, should be YYYY-MM-DD: {value}")

    return result_value


def set_date_field(value):
    """Parse a CSV date cell (YYYY-MM-DD) into a `date` for DateField columns."""
    result_value = set_datetime_field(value)
    return result_value.date() if result_value else None


def set_fk_field(row, key):
    obj = None
    value = row[key]

    try:
        model_class_name = string.capwords(key, sep="_").replace("_", "")
        ModelClass = apps.get_model(f"core.{model_class_name}")
        obj = ModelClass.objects.get(name__iexact=value)
    except ModelClass.DoesNotExist as does_not_exist_error:
        raise ObjectDoesNotExist(f"{does_not_exist_error} for {model_class_name} {value}")
    except ModelClass.MultipleObjectsReturned as multiple_objects_returned_error:
        raise IntegrityError(f"{multiple_objects_returned_error} for {model_class_name} {value}")
    except IntegrityError as integrity_error:
        raise IntegrityError(f"{integrity_error} for {model_class_name} {value}")

    return obj.id if obj else None


def create_fk_obj(*, model_class, instance_key, instance_value):
    # instance, created = ModelClass.objects.get_or_create(name=row[fk_field])
    # Get objects with case insensitive lookup or create a new object.
    # Needs to check if dealing with a soft-delete enabled model.
    # print(f"{model_class=}; {instance_key=}: {instance_value=}")

    instance_key_iexact = f"{instance_key}__iexact"
    defaults = {
        instance_key: instance_value,
    }

    if hasattr(model_class, "with_softdeleted_objects"):
        instance, created = model_class.with_softdeleted_objects.get_or_create(
            **{instance_key_iexact: instance_value},
            # name__iexact=instance_value,
            defaults=defaults,
        )

        # Ensure previously soft-deleted objects gets undeleted
        instance.deleted_at = None
        instance.deleted_by = None
        instance.save()
    else:
        instance, created = model_class.objects.get_or_create(
            # name__iexact=instance_value,
            **{instance_key_iexact: instance_value},
            defaults=defaults,
        )

    return instance


def create_fk_objs(fk_field, rows):
    model_class_name = string.capwords(fk_field, sep="_").replace("_", "")
    model_class = apps.get_model(f"core.{model_class_name}")

    for row in rows:
        create_fk_obj(model_class=model_class, instance_key="name", instance_value=row[fk_field])

    return


def get_or_create_person(*, first_name, last_name, email, organizational_unit=None):
    """
    Get or create a core.Person keyed on their (unique) email address.

    The email is normalized to lowercase before lookup and storage. As Person
    is a soft-delete model, the lookup uses the soft-delete-aware manager and
    undeletes a previously soft-deleted match to avoid a unique-email
    IntegrityError.
    """
    from dlcdb.core.models import Person

    email = (email or "").strip().lower()
    if not email:
        raise ValidationError("A LENDER_EMAIL is required to import a LENT record.")

    person, created = Person.with_softdeleted_objects.get_or_create(
        email__iexact=email,
        defaults={
            "first_name": (first_name or "").strip(),
            "last_name": (last_name or "").strip(),
            "email": email,
            "organizational_unit": organizational_unit,
        },
    )

    # Ensure a previously soft-deleted person gets undeleted:
    if person.deleted_at or person.deleted_by:
        person.deleted_at = None
        person.deleted_by = None
        person.save()

    return person
