from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Prefetch

from ..core.models import Device, Person, LentRecord
from .serializers import DeviceSerializer, RecordSerializer, PersonSerializer


class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows devices to be viewed.
    """
    queryset = (
        Device
        .objects
        .all()
        .select_related('active_record', 'active_record__room', 'device_type')
    )
    serializer_class = DeviceSerializer
    lookup_field = 'uuid'
    search_fields = ['edv_id', 'sap_id']
    filter_backends = [SearchFilter, filters.DjangoFilterBackend]
    filterset_fields = ['edv_id', 'uuid', 'device_type__prefix', 'active_record__record_type']


class RecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows active records to be viewed.
    """
    queryset = LentRecord.objects.select_related('device')
    serializer_class = RecordSerializer


class PersonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list lended devices for persons. Currently used to
    satisfy requests from the UDB.
    """
    serializer_class = PersonSerializer
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
