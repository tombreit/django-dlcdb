from dataclasses import dataclass
from django.conf import settings
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import pluralize

from dlcdb.core.models import Room, Device


def branding(request):
    """Make branding settings available for all requests."""
    return settings.BRANDING


def hints(request):
    """Display some pre-defined messages as sticky messages"""

    sticky_messages = []

    @dataclass
    class StickyMessage:
        """Custom message class for our sticky messages."""
        level: str
        msg: str
        cta_link: str
        cta_text: str

        def get_formatted_msg(self) -> str:
            """Build a html safe message with a call-to-action link."""
            return format_html("{} <a href='{}'>{}</a>",
                self.msg,
                self.cta_link,
                self.cta_text,
            )

    rooms_changelist_url = reverse('admin:core_room_changelist')

    if not any([
        request.path_info.startswith("/admin/login/"),
        request.path_info.startswith("/admin/logout/"),
    ]):

        if Device.objects.filter(active_record__isnull=True).exists():
            devices_wo_record_changelist = f"{reverse('admin:core_device_changelist')}?has_record=has_no_record"
            recordless_devices_count = Device.objects.filter(active_record__isnull=True).count()
            sticky_messages.append(
                StickyMessage(
                    level=messages.WARNING,
                    msg=_(f"{recordless_devices_count} Device{pluralize(recordless_devices_count)} without record!"),
                    cta_link=devices_wo_record_changelist,
                    cta_text=_("Add proper record?"),
                )
            )

        if Room.objects.exists():

            if not Room.objects.filter(is_external=True).exists():
                sticky_messages.append(
                    StickyMessage(
                        level=messages.WARNING,
                        msg=_("No room configured as 'is_external'!"),
                        cta_link=rooms_changelist_url,
                        cta_text=_("Configure one?"),
                    )
                )

            if not Room.objects.filter(is_auto_return_room=True).exists():
                sticky_messages.append(
                    StickyMessage(
                        level=messages.WARNING,
                        msg=_("No room configured as 'is_auto_return_room'!"),
                        cta_link=rooms_changelist_url,
                        cta_text=_("Configure one?"),
                    )
                )

        else:
            sticky_messages.append(
                StickyMessage(
                    level=messages.WARNING,
                    msg=_("No rooms defined yet."),
                    cta_link=rooms_changelist_url,
                    cta_text=_("Add some rooms?"),
                )
            )


    for message in sticky_messages:
        messages.add_message(request, message.level, message.get_formatted_msg())

    return {}  # empty dict to make context_processor happy
