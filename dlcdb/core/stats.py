from .models.device import Device
from .models.device_type import DeviceType

from .models.prx_inroomrecord import InRoomRecord
from .models.prx_lentrecord import LentRecord
from .models.prx_lostrecord import LostRecord
from .models.prx_orderedrecord import OrderedRecord


def get_record_fraction_data():
    """
    Returns chartjs-ready datasets to display the fraction of each record.
    :return:
    """

    room_records_count = InRoomRecord.objects.filter(is_active=True).count()
    lent_records_count = LentRecord.objects.filter(is_active=True).count()
    lost_records_count = LostRecord.objects.filter(is_active=True).count()
    ordered_records_count = OrderedRecord.objects.filter(is_active=True).count()

    record_fraction_data = dict(
        labels=['Lokalisiert', 'Verliehen', 'Nicht lokalisiert', 'Bestellt'],
        datasets=[
            dict(
                label='Geräte nach Verbleib',
                data=[room_records_count, lent_records_count, lost_records_count, ordered_records_count],
                backgroundColor=[
                    "#FFCE56",
                    "#FF6384",
                    "#36A2EB",

                ],
                hoverBackgroundColor=[
                    "#FFCE56",
                    "#FF6384",
                    "#36A2EB",
                ]
            )
        ]
    )
    return record_fraction_data


def get_device_type_data():
    """
    Returns chartjs-ready datasets to display the amount of each device type.
    :return:
    """
    device_type_data = dict(labels=[], datasets=[dict(label='Geräte nach Typ', data=[])])

    for elem in DeviceType.objects.all():
        device_type_data['labels'].append(elem.name)
        device_type_data['datasets'][0]['data'].append(Device.objects.filter(device_type=elem).count())
    return device_type_data


def get_devices_by_series_data():
    """
    Returns chartjs-ready datasets to display the amount of each device type.
    :return:
    """
    from django.db.models import Count
    qs = Device.objects.values('series').annotate(total=Count('series'))
    print(qs)

    data = dict(labels=[], datasets=[dict(label='Geräte nach Typ', data=[])])
    for elem in qs:
        data['labels'].append(elem['series'])
        data['datasets'][0]['data'].append(elem['count'])
