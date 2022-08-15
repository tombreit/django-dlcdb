from django.db.models import Count, Q, IntegerField

from .models.record import Record
from .models.device import Device
from .models.device_type import DeviceType

from .models.prx_inroomrecord import InRoomRecord
from .models.prx_lentrecord import LentRecord
from .models.prx_lostrecord import LostRecord
from .models.prx_removedrecord import RemovedRecord


def get_record_fraction_data():
    """
    Returns chartjs-ready datasets to display the fraction of each record.
    :return:
    """

    room_records_count = InRoomRecord.objects.filter(is_active=True).count()
    lent_records_count = LentRecord.objects.filter(is_active=True).count()
    lost_records_count = LostRecord.objects.filter(is_active=True).count()
    removed_records_count = RemovedRecord.objects.filter(is_active=True).count()

    record_fraction_data = dict(
        labels=['Lokalisiert', 'Verliehen', 'Nicht auffindbar', 'Entfernt'],
        datasets=[
            dict(
                label='Geräte nach Verbleib',
                data=[room_records_count, lent_records_count, lost_records_count, removed_records_count],
                # backgroundColor=[
                #     "#FFCE56",
                #     "#FF6384",
                #     "#36A2EB",
                #     "red",

                # ],
                # hoverBackgroundColor=[
                #     "#FFCE56",
                #     "#FF6384",
                #     "#36A2EB",
                #     "red",
                # ]
            )
        ]
    )
    return record_fraction_data


def get_device_type_data():
    """
    Returns chartjs-ready datasets to display the amount of each device type.
    :return:
    """

    device_type_data = dict(labels=[], datasets=[dict(label='Geräte nach Typ (>10)', data=[])])

    # for elem in DeviceType.objects.all():
    #     if Device.objects.filter(device_type=elem).count() > 5:
    #         device_type_data['labels'].append(elem.name)
    #         device_type_data['datasets'][0]['data'].append(Device.objects.filter(device_type=elem).count())

    device_types_qs = (
        DeviceType.objects
        .annotate(
            count=Count('device')
        )
        .exclude(count__lt=10)
        .order_by('-count')
    )

    for dt in device_types_qs:
        # print(f"{dt.name}: {dt.count}")
        device_type_data['labels'].append(dt.name)
        device_type_data['datasets'][0]['data'].append(dt.count)

    return device_type_data


def get_devices_by_series_data():
    """
    Returns chartjs-ready datasets to display the amount of each device type.
    :return:
    """
    from django.db.models import Count
    qs = Device.objects.values('series').annotate(total=Count('series'))

    data = dict(labels=[], datasets=[dict(label='Geräte nach Typ', data=[])])
    for elem in qs:
        data['labels'].append(elem['series'])
        data['datasets'][0]['data'].append(elem['count'])


def get_notebooks_lending_data():
    # all_ntbs = LentRecord.objects.filter(device__device_type__prefix="ntb").count()
    assigned_ntbs = LentRecord.objects.filter(device__device_type__prefix="ntb").filter(record_type=Record.LENT).count()
    not_assigned_ntbs = LentRecord.objects.filter(device__device_type__prefix="ntb").filter(~Q(record_type=Record.LENT)).count()

    data = dict(labels=[], datasets=[dict(label='Freie Notebooks', data=[], backgroundColor=["orange", "red"])],)

    _labels = ['NTBs verliehen', 'NTBs verfügbar']

    data['labels'].extend(_labels)
    data['datasets'][0]['data'].extend([assigned_ntbs, not_assigned_ntbs])

    return data

