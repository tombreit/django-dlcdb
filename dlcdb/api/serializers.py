from rest_framework import serializers

from ..core.models import Device, Record, Person, LentRecord


class DeviceSerializer(serializers.HyperlinkedModelSerializer):
    record_type = serializers.StringRelatedField(
        source='active_record.record_type',
    )
    room = serializers.StringRelatedField(
        source='active_record.room.number',
    )
    room_nickname = serializers.StringRelatedField(
        source='active_record.room.nickname',
    )
    lender = serializers.StringRelatedField(
        source='active_record.person',
    )
    url = serializers.HyperlinkedIdentityField(
        view_name='device-detail',
        lookup_field='uuid'
    )
    device_type_name = serializers.StringRelatedField(
        source='device_type.name',
    )
    device_type_prefix = serializers.StringRelatedField(
        source='device_type.prefix',
    )

    class Meta:
        model = Device
        lookup_field = 'uuid'
        fields = [
            'url',
            'uuid',
            'edv_id',
            'sap_id',
            'manufacturer',
            'series',
            'device_type_name',
            'device_type_prefix',
            'record_type',
            'room',
            'room_nickname',
            'lender',
        ]


class RecordSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Record
        fields = [
            'pk',
            'device',
            'record_type',
            'is_active',
        ]


class LendingsSerializer(serializers.ModelSerializer):
    device_desc = serializers.StringRelatedField(
        source='get_lent_string_repr',
    )

    class Meta:
        model = LentRecord
        fields = [
            # 'pk',
            # 'person',
            # 'device',
            # 'is_active',
            'record_type',
            'device_desc',
        ]


class PersonSerializer(serializers.HyperlinkedModelSerializer):
    lending = LendingsSerializer(
        many=True,
        read_only=True,
        source='lent_records',
    )

    class Meta:
        model = Person
        fields = [
            # 'pk',
            'udb_person_uuid',
            'last_name',
            'first_name',
            'udb_person_email_internal_business',
            'lending',
        ]
