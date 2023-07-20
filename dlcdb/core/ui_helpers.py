from dataclasses import dataclass, field

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .models.record import Record


@dataclass
class UIRecordActionSnippetContext:
    """
    infos: Returns a list of dicts with infos for the current state of the
    device.
    add_links: Returns a list of dicts each representing an add link in order to display
    dropdowns to create records for a given device.
    """
    device_obj: object
    for_view: str
    record_infos: list = field(init=False)
    add_links: list = field(init=False)

    def __post_init__(self):
        self.record_infos = self._record_infos
        self.add_links = self._add_links
        self.active_record = self.device_obj.active_record
        self.device_pk = self.device_obj.pk

    def _record_infos(self):
        record_infos = []

        if self.active_record:

            inroom_url = None
            if self.active_record.room:
                if self.for_view == "inventory":
                    inroom_url = f"{reverse('inventory:inventorize-room', kwargs={'pk': self.active_record.room.pk})}"
                else:
                    inroom_url = f"{reverse('admin:core_device_changelist')}?active_record__room__id__exact={self.active_record.room.id}"

            if self.active_record.room:
                record_infos.append(dict(
                    css_classes="btn btn-info",
                    title="{text} {obj}".format(text=_('In room'), obj=self.active_record.room.number),
                    url=inroom_url,
                    label=self.active_record.room.number,
                ))

            # Common infos for all record types
            record_type = self.active_record.record_type
            record_type_info = {}

            if record_type == Record.INROOM:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    title=_("Relocate device"),
                    url=f"{reverse('core:core_devices_relocate')}?ids={self.device_pk}",
                    label=self.active_record.get_record_type_display,
                )
            elif record_type == Record.LENT:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    url=reverse("admin:core_lentrecord_change", args=[self.active_record]),
                    label=f"an {self.active_record.person }",
                    title=_("Edit lending"),
                )
            elif record_type == Record.ORDERED:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    label=self.device_obj.get_record_type_display,
                )
            elif record_type == Record.REMOVED:
                record_type_info = dict(
                    css_classes="btn btn-warning",
                    url=reverse("admin:core_record_change", args=[self.device_pk]),
                    label=self.active_record.get_record_type_display,
                )
            elif record_type == Record.LOST:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f"{reverse('admin:core_record_changelist')}?device__id__exact={self.device_pk}",
                    label=self.active_record.get_record_type_display,
                    title=_("Show previous records for this device"),
                )
            else:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f'{reverse("admin:core_record_changelist")}?device__id__exact={self.device_pk}',
                    label=_("Unknown record type! Contact your administrator!"),
                )

            record_infos.append(record_type_info)

        else:
            record_infos.append(dict(
                label="No current record",
                css_classes="btn btn-warning disabled",
            ))

        return record_infos


    def _add_links(self):
        add_links = []

        if self.active_record:
            for record_value, record_label in Record.RECORD_TYPE_CHOICES:

                if record_value == Record.ORDERED:
                    # We do not expose this Record type for now
                    continue
                elif record_value == Record.REMOVED and self.active_record.record_type == Record.REMOVED:
                    # Do not let already removed devices removed again
                    continue
                elif record_value == Record.LOST and self.active_record.record_type == Record.LOST:
                    # Lost records could not be lost again
                    continue
                elif record_value == Record.LOST and self.device_obj.is_lentable:
                    # Device is lentable, but does not have a prior INROOM record
                    continue
                elif record_value == Record.LENT and self.active_record.record_type == Record.LOST:
                    # Device is lentable, but does not have a prior INROOM record
                    continue
                elif record_value == Record.LENT and self.active_record.record_type == Record.LENT:
                    # Device is currently already on loan.
                    # add_links.append(dict(
                    #     url=reverse("admin:core_lentrecord_change", args=[self.active_record]),
                    #     label=_('Lending'),
                    # ))
                    continue
                elif record_value == Record.LENT and self.device_obj.is_lentable:
                    # Device is available for rent
                    add_links.append(dict(
                        url=f"{reverse('admin:core_lentrecord_changelist')}?q={self.device_obj.uuid}",
                        label=_('Lend'),
                    ))
                elif record_value == Record.LENT and not self.device_obj.is_lentable:
                    continue
                else:
                    add_links.append(dict(
                        label=record_label,
                        url=f"{Record.get_proxy_model_by_record_type(record_value).get_admin_action_url()}?device={self.device_pk}"
                    ))

        else:
            # Currently no active record set (new device).
            # Only allow a first INROOM record.
            add_links.append(dict(
                url=f'{reverse("admin:core_inroomrecord_add")}?device={self.device_pk}',
                label=_('Locate'),
            ))

        return add_links
