# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from dlcdb.lending.models import LendingProfile
from dlcdb.core.models.prx_lentrecord import LentRecord


def print_lent_sheet(request, pk):
    record = get_object_or_404(LentRecord, pk=pk)

    device_type = record.device.device_type
    if not device_type:
        raise Http404("Device has no device type assigned.")

    try:
        profile = LendingProfile.objects.get(device_type=device_type)
    except LendingProfile.DoesNotExist:
        raise Http404(f"No lending profile configured for device type '{device_type}'.")

    template_name = f"lending/db/{profile.pk}.html"
    context = {
        "record": record,
        "lending_profile": profile,
    }
    return TemplateResponse(request, template_name, context)
