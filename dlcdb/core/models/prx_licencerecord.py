# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from datetime import datetime, timedelta

from django.db import models
from django.db.models import Q, Case, CharField, Value, When
from django.db.models.expressions import RawSQL
from django.utils.translation import gettext_lazy as _

from .record import Record


class BaseLicenceRecordManager(models.Manager):
    def get_queryset(self):
        removed_records = Q(Q(record_type=Record.REMOVED))

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
            .exclude(removed_records)
            # .prefetch_related("device__subscription_set")
            .order_by("-modified_at")
        )

        # Annotate with licence state
        today = datetime.today().date()

        # TODO: make threshold configurable
        expiration_warning_threshold = today + timedelta(days=93)

        # Raw SQL for distinct emails concatenated with newlines
        subscribers_subquery = """
            SELECT GROUP_CONCAT(distinct_email, char(10))
            FROM (
                SELECT DISTINCT p.email as distinct_email
                FROM core_person p
                INNER JOIN notifications_subscription s ON s.subscriber_id = p.id
                WHERE s.device_id = core_device.id
                AND p.email IS NOT NULL
                ORDER BY p.email
            )
        """

        # TODO: use descriptive license_state wording like "expires_soon", "expired" instead of "80-warning"
        qs = qs.annotate(
            get_subscribers=models.ExpressionWrapper(RawSQL(subscribers_subquery, []), output_field=CharField()),
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
