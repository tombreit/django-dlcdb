# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime, timedelta

from django.db import models
from django.db.models import Q, Case, CharField, Value, When

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
        now = datetime.today().date()

        # TODO: make threshold configurable
        threshold = now + timedelta(days=30)

        # TODO: use descriptive license_state wording like "expires_soon", "expired" instead of "80-warning"
        qs = (
            qs.select_related("device", "device__manufacturer", "device__device_type")
            .prefetch_related("device__notification_set")
            .annotate(
                licence_state=Case(
                    When(
                        device__contract_expiration_date__lte=now,
                        then=Value("90-danger"),
                    ),
                    When(
                        device__contract_expiration_date__gt=now,
                        device__contract_expiration_date__lte=threshold,
                        then=Value("80-warning"),
                    ),
                    default=Value("10-unknown"),
                    output_field=CharField(),
                )
            )
            .order_by("-licence_state", "device__contract_expiration_date")
        )

        return qs


class LicenceRecord(Record):
    objects = BaseLicenceRecordManager()

    def get_human_title(self):
        return f"{self.device.manufacturer} - {self.device.series}"

    def __str__(self):
        return self.device.edv_id

    class Meta:
        proxy = True
        verbose_name = "Lizenz"
        verbose_name_plural = "Lizenzen"
