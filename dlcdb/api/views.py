from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Prefetch

from ..core.models import Device, Person, LentRecord, Room
from . import serializers


class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows devices to be viewed.
    """
    queryset = (
        Device
        .objects
        .all()
        .select_related(
            'active_record__person',
            'active_record__room',
            'device_type',
            'manufacturer',
        )
    )
    serializer_class = serializers.DeviceSerializer
    lookup_field = 'uuid'
    search_fields = ['edv_id', 'sap_id']
    filter_backends = [SearchFilter, filters.DjangoFilterBackend]
    filterset_fields = ['edv_id', 'uuid', 'device_type__prefix', 'active_record__record_type']


class LentRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows active lendings to be viewed.
    """
    queryset = LentRecord.objects.filter(is_active=True)
    serializer_class = serializers.LentRecordSerializer


class RoomViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for base room data
    """
    queryset = Room.objects.all()
    serializer_class = serializers.RoomSerializer
    lookup_field = 'uuid'


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list lended devices for persons. Currently used to
    satisfy requests from the UDB.
    """
    serializer_class = serializers.PersonSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'first_name',
        'last_name',
        'email',
        'udb_person_uuid',
    ]
    queryset = (
        Person
        .objects
        .all()
        .prefetch_related(
            Prefetch(
                'record_set',
                queryset=LentRecord.objects.all(),
                to_attr='lent_records',
            ),
        )
    )
