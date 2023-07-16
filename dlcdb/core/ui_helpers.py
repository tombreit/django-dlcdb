from dataclasses import dataclass, field

from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@dataclass
class UIRecordActionSnippetContext:
    """
    infos: Returns a list of dicts with infos for the current state of the
    device.
    add_links: Returns a list of dicts each representing an add link in order to display
    dropdowns to create records for a given device.
    """
    record_obj: object
    record_class: object = field(init=False)
    record_infos: list = field(init=False)
    add_links: list = field(init=False)

    def __post_init__(self):
        self.record_class = type(self.record_obj)
        self.record_infos = self._record_infos()
        self.add_links = self._add_links()

    def _record_infos(self):
        record_infos = []

        if not self.record_obj:
            record_infos.append(dict(
                label="No current record",
                css_classes="btn btn-warning disabled",
            ))
        else:
            device_pk = self.record_obj.device.pk

            if self.record_obj.room:
                record_infos.append(dict(
                    css_classes="btn btn-info",
                    title="{text} {obj}".format(text=_('In room'), obj=self.record_obj.room.number),
                    url=f"{reverse('admin:core_device_changelist')}?record__room__id__exact={self.record_obj.room.id}",
                    label=self.record_obj.room.number,
                ))

            # Common infos for all record types
            record_type = self.record_obj.record_type
            record_type_info = {}

            if record_type == self.record_class.INROOM:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    title=_("Relocate device"),
                    url=f"{reverse('core:core_devices_relocate')}?ids={device_pk}",
                    label=self.record_obj.get_record_type_display,
                )
            elif record_type == self.record_class.LENT:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    url=reverse("admin:core_lentrecord_change", args=[self.record_obj.pk]),
                    label=f"an {self.record_obj.person }",
                    title=_("Edit lending"),
                )
            elif record_type == self.record_class.ORDERED:
                record_type_info = dict(
                    css_classes="btn btn-info",
                    label=self.record_obj.get_record_type_display,
                )
            elif record_type == self.record_class.REMOVED:
                record_type_info = dict(
                    css_classes="btn btn-warning",
                    url=reverse("admin:core_record_change", args=[self.record_obj.pk]),
                    label=self.record_obj.get_record_type_display,
                )
            elif record_type == self.record_class.LOST:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f"{reverse('admin:core_record_changelist')}?device__id__exact={device_pk}",
                    label=self.record_obj.get_record_type_display,
                    title=_("Show previous records for this device"),
                )
            else:
                record_type_info = dict(
                    css_classes="btn btn-danger",
                    url=f'{reverse("admin:core_record_changelist")}?device__id__exact={device_pk}',
                    label=_("Unknown record type! Contact your administrator!"),
                )

            record_infos.append(record_type_info)

        return record_infos


    def _add_links(self):
        add_links = []

        for record_value, record_label in self.record_class.RECORD_TYPE_CHOICES:
            if record_value == self.record_class.ORDERED:
                continue
            elif record_value == self.record_class.REMOVED and self.record_obj and self.record_obj.record_type == self.record_class.REMOVED:
                # Do not let already removed devices removed again
                continue
            elif record_value == self.record_class.LOST and self.record_obj and self.record_obj.record_type == self.record_class.LOST:
                # Lost records could not be lost again
                continue
            elif record_value == self.record_class.LENT:
                if self.record_obj and self.record_obj.record_type == self.record_class.LENT:
                    add_links.append(dict(
                        url=reverse("admin:core_lentrecord_change", args=[self.record_obj.pk]),
                        label=_('Lending'),
                    ))
                elif self.record_obj and self.record_obj.device.is_lentable:
                    add_links.append(dict(
                        url=reverse('admin:core_lentrecord_change', args=[self.record_obj.pk]),
                        label=_('Lend'),
                    ))
            else:
                add_links.append(dict(
                    label=record_label,
                    url=f"{self.record_class.get_proxy_model_by_record_type(record_value).get_admin_action_url()}?device={self.record_obj.device.id}"
                ))

        return add_links
