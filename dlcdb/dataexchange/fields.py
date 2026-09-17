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
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.utils.timezone import make_aware
from django.utils.translation import gettext as _


def set_datetime_field(value, *, column=None):
    """Parse a CSV date cell (YYYY-MM-DD) into an aware `datetime`.

    ``column`` names the CSV column in the error message. Without it a bad cell
    only says *that* a date is malformed, leaving the user to guess which of the
    seven date columns of the row it came from.
    """
    result_value = None

    if value:
        try:
            result_value = datetime.strptime(value, "%Y-%m-%d")
            result_value = make_aware(result_value)
        except ValueError:
            prefix = f"{column}: " if column else ""
            raise ValueError(
                _("%(prefix)sincorrect date format, should be YYYY-MM-DD: '%(value)s'")
                % {"prefix": prefix, "value": value}
            )

    return result_value


def set_date_field(value, *, column=None):
    """Parse a CSV date cell (YYYY-MM-DD) into a `date` for DateField columns."""
    result_value = set_datetime_field(value, column=column)
    return result_value.date() if result_value else None


def set_fk_field(row, key):
    value = row[key]
    # An empty cell means "no value": these FKs are nullable, so resolve to NULL
    # rather than inventing a nameless DeviceType/Manufacturer/Supplier.
    if not value:
        return None

    model_class_name = string.capwords(key, sep="_").replace("_", "")
    # Resolved outside the try below: a lookup failure here is a coding error in
    # the column list, not bad user data, and binding it inside would leave
    # ModelClass undefined in the except clauses.
    ModelClass = apps.get_model(f"core.{model_class_name}")

    try:
        obj = ModelClass.objects.get(name__iexact=value)
    except ModelClass.DoesNotExist:
        raise ObjectDoesNotExist(
            _("%(column)s: no %(model)s named '%(value)s' exists.")
            % {"column": key, "model": model_class_name, "value": value}
        )
    except ModelClass.MultipleObjectsReturned:
        raise IntegrityError(
            _("%(column)s: '%(value)s' is ambiguous, several %(model)s entries match it.")
            % {"column": key, "model": model_class_name, "value": value}
        )

    return obj.id


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
        instance, _created = model_class.with_softdeleted_objects.get_or_create(
            **{instance_key_iexact: instance_value},
            # name__iexact=instance_value,
            defaults=defaults,
        )

        # Ensure previously soft-deleted objects gets undeleted
        instance.deleted_at = None
        instance.deleted_by = None
        instance.save()
    else:
        instance, _created = model_class.objects.get_or_create(
            # name__iexact=instance_value,
            **{instance_key_iexact: instance_value},
            defaults=defaults,
        )

    return instance


def create_fk_objs(fk_field, rows):
    model_class_name = string.capwords(fk_field, sep="_").replace("_", "")
    model_class = apps.get_model(f"core.{model_class_name}")

    for row in rows:
        value = row.get(fk_field)
        # Skip blanks (and the None a short CSV row yields): creating a nameless
        # object here used to fail with a NOT NULL constraint error carrying no
        # row context at all.
        if not value:
            continue
        create_fk_obj(model_class=model_class, instance_key="name", instance_value=value)


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
        raise ValidationError(_("LENDER_EMAIL: a lender email address is required to import a LENT record."))

    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    try:
        person, _created = Person.with_softdeleted_objects.get_or_create(
            email__iexact=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "organizational_unit": organizational_unit,
            },
        )
    except IntegrityError as integrity_error:
        # Lookup is keyed on the email, but Person also carries a
        # UniqueConstraint on lower(first_name) + lower(last_name). A new email
        # for an existing name -- or two rows that both leave the name columns
        # blank -- therefore hits the database rather than the lookup, and the
        # bare constraint text names neither the person nor the row. Person.clean()
        # phrases this well but get_or_create() never calls full_clean().
        raise ValidationError(
            _(
                "Could not import lender '%(email)s': a different person is already "
                "stored under the name '%(first_name)s %(last_name)s' "
                "(names must be unique). Original error: %(error)s"
            )
            % {
                "email": email,
                "first_name": first_name or "—",
                "last_name": last_name or "—",
                "error": integrity_error,
            }
        ) from integrity_error

    # Ensure a previously soft-deleted person gets undeleted:
    if person.deleted_at or person.deleted_by:
        person.deleted_at = None
        person.deleted_by = None
        person.save()

    return person
