# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from rest_framework import viewsets
from rest_framework.filters import SearchFilter
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter

from django_filters import rest_framework as filters

from django.db.models import Prefetch

from ..core.models import Device, Person, LentRecord, Room
from . import serializers


@extend_schema(exclude=True)
@api_view(["GET"])
def api_root(request):
    return Response({"message": "DLCDB API v2 root"})


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="search",
            description="Search devices by EDV-ID or SAP-ID (inventar number) or series.",
            required=False,
            type=str,
        ),
    ]
)
class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows devices to be viewed.
    """

    queryset = Device.objects.all().select_related(
        "active_record__person",
        "active_record__room",
        "device_type",
        "manufacturer",
    )
    serializer_class = serializers.DeviceSerializer
    lookup_field = "uuid"
    search_fields = ["edv_id", "sap_id", "series"]
    filter_backends = [SearchFilter, filters.DjangoFilterBackend]
    filterset_fields = {
        "edv_id": ["exact"],
        "uuid": ["exact"],
        "device_type__prefix": ["exact"],
        "manufacturer__name": ["iexact"],
        "active_record__record_type": ["exact"],
    }


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="search",
            description="Search by device series, EDV-ID, or person last name.",
            required=False,
            type=str,
        ),
    ]
)
class LentRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows active lendings to be viewed.
    """

    queryset = LentRecord.objects.filter(is_active=True).select_related(
        "device",
        "person",
    )
    serializer_class = serializers.LentRecordSerializer
    filter_backends = [SearchFilter]
    search_fields = ["device__series", "device__edv_id", "person__last_name"]


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for base room data
    """

    queryset = Room.objects.all()
    serializer_class = serializers.RoomSerializer
    lookup_field = "uuid"


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list lended devices for persons. Currently used to
    satisfy requests from the UDB.
    """

    serializer_class = serializers.PersonSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = [
        "first_name",
        "last_name",
        "email",
        "udb_person_uuid",
    ]
    queryset = Person.objects.all().prefetch_related(
        Prefetch(
            "record_set",
            queryset=LentRecord.objects.filter(is_active=True),
            to_attr="lent_records",
        ),
    )
