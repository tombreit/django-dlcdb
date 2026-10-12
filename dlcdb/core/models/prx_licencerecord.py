# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import timedelta

from django.db import models
from django.db.models import Case, CharField, Value, When
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .record import Record

# A running licence is "expiring" from this many days before its contract expiration date.
EXPIRING_WITHIN_DAYS = 93


class BaseLicenceRecordManager(models.Manager):
    def get_queryset(self):
        # Basic queryset
        qs = (
            super()
            .get_queryset()
            .select_related(
                "device",
                "device__manufacturer",
                "device__supplier",
                "device__device_type",
            )
            .filter(
                is_active=True,
                device__is_licence=True,
            )
            .exclude(record_type=Record.REMOVED)
            .order_by("-modified_at")
        )

        # Annotate with licence state
        today = timezone.localdate()
        expiration_warning_threshold = today + timedelta(days=EXPIRING_WITHIN_DAYS)

        qs = qs.annotate(
            license_state=Case(
                # Ordering matters: the first When() condition that is met will be used.
                When(
                    device__contract_termination_date__isnull=False,
                    then=Value("terminated"),
                ),
                When(
                    device__contract_start_date__lte=today,
                    device__contract_expiration_date__gt=today,
                    device__contract_expiration_date__lte=expiration_warning_threshold,
                    then=Value("expiring"),
                ),
                When(
                    device__contract_expiration_date__lte=today,
                    then=Value("expired"),
                ),
                When(
                    device__created_at__date__lte=today,
                    device__contract_start_date__gt=today,
                    then=Value("ordered"),
                ),
                When(
                    device__contract_start_date__lte=today,
                    device__contract_expiration_date__gt=today,
                    then=Value("active"),
                ),
                default=Value("10-unknown"),
                output_field=CharField(),
            ),
        ).order_by("-license_state", "device__contract_expiration_date")

        return qs


class LicenceRecord(Record):
    objects = BaseLicenceRecordManager()

    @staticmethod
    def get_localized_license_state_label(for_state=None):
        """
        Provide human labels for the license queryset annotations.
        """
        LICENSE_STATE_LABELS = {
            "ordered": _("Ordered"),
            "active": _("Active"),
            "expiring": _("Expiring"),
            "expired": _("Expired"),
            "terminated": _("Terminated"),
        }
        label = LICENSE_STATE_LABELS.get(for_state, _("Unknown"))
        return label

    def get_license_state_label(self):
        return self.get_localized_license_state_label(for_state=self.license_state)

    def __str__(self):
        return f"{self.pk}"

    class Meta:
        proxy = True
        verbose_name = _("License")
        verbose_name_plural = _("Licenses")
