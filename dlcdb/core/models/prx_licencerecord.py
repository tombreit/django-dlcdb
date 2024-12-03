# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime, timedelta

from django.db import models
from django.db.models import Q, Case, CharField, Value, When
from django.utils.translation import gettext_lazy as _

from .record import Record


class BaseLicenceRecordManager(models.Manager):
    def get_queryset(self):
        removed_records = Q(Q(record_type=Record.REMOVED))

        # Basic queryset
        qs = (
            super()
            .get_queryset()
            .filter(
                is_active=True,
                device__is_licence=True,
            )
            .exclude(removed_records)
            .order_by("-modified_at")
        )

        # Annotate with licence state
        today = datetime.today().date()

        # TODO: make threshold configurable
        expiration_warning_threshold = today + timedelta(days=93)

        # TODO: use descriptive license_state wording like "expires_soon", "expired" instead of "80-warning"
        qs = (
            qs.select_related("device", "device__manufacturer", "device__device_type")
            .prefetch_related("device__notification_set")
            .annotate(
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
                    # When(
                    #     device__contract_expiration_date__lte=now,
                    #     then=Value("90-danger"),
                    # ),
                    # When(
                    #     device__contract_expiration_date__gt=now,
                    #     device__contract_expiration_date__lte=expiration_warning_threshold,
                    #     then=Value("80-warning"),
                    # ),
                    default=Value("10-unknown"),
                    output_field=CharField(),
                )
            )
            .order_by("-license_state", "device__contract_expiration_date")
        )

        return qs


class LicenceRecord(Record):
    objects = BaseLicenceRecordManager()

    def get_human_title(self):
        return f"{self.device.manufacturer} - {self.device.series}"

    def get_license_state_label(self):
        """
        Provide human labels for the license queryset annotations.
        """

        state = self.license_state
        label = _("Unknown")

        if state == "ordered":
            label = _("Ordered")
        elif state == "active":
            label = _("Active")
        elif state == "expiring":
            label = _("Expiring")
        elif state == "expired":
            label = _("Expired")
        elif state == "terminated":
            label

        return label

    def __str__(self):
        return self.device.edv_id

    class Meta:
        proxy = True
        verbose_name = "Lizenz"
        verbose_name_plural = "Lizenzen"
