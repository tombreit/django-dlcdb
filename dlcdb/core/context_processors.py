# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from dataclasses import dataclass

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Min, Q
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from dlcdb.core.models import Device, Room
from dlcdb.dataexchange.models import ImporterList


def hints(request):
    """Display some pre-defined messages as sticky messages"""

    # Anonymous visitors (e.g. the login page) neither need the hints nor can
    # act on them; this also spares their requests the hint queries.
    if not request.user.is_authenticated:
        return {}

    sticky_messages = []

    @dataclass
    class StickyMessage:
        """Custom message class for our sticky messages."""

        level: str
        msg: str
        cta_link: str = ""
        cta_text: str = ""

        def get_formatted_msg(self) -> str:
            """Build a html safe message, with a call-to-action link if given."""
            if not self.cta_link:
                return format_html("{}", self.msg)
            return format_html(
                "{} <a href='{}'>{}</a>",
                self.msg,
                self.cta_link,
                self.cta_text,
            )

    if not any(
        [
            request.path_info.startswith("/admin/login/"),
            request.path_info.startswith("/admin/logout/"),
        ]
    ):
        rooms_index_url = reverse("rooms:index")
        user = request.user

        # One query for both device hints: record-less devices of the user's
        # tenants, and devices without tenant (global: they belong to no tenant).
        recordless = Q(tenant__in=request.tenants, active_record__isnull=True)
        device_counts = Device.objects.aggregate(
            recordless_count=Count("pk", filter=recordless),
            recordless_single_pk=Min("pk", filter=recordless),
            without_tenant_count=Count("pk", filter=Q(tenant__isnull=True)),
        )
        recordless_devices_count = device_counts["recordless_count"]

        if recordless_devices_count:
            if recordless_devices_count == 1:
                # A single device: jump straight into Move with it preselected.
                cta_link = f"{reverse('assets:relocate')}?device={device_counts['recordless_single_pk']}"
            else:
                # Several devices: the device list filtered to record-less
                # devices; each detail page offers the Move action from there.
                from dlcdb.assets.filters import STATE_NO_RECORD

                cta_link = f"{reverse('assets:device_index')}?state={STATE_NO_RECORD}"

            sticky_messages.append(
                StickyMessage(
                    level=messages.WARNING,
                    msg=ngettext(
                        "%(count)d device without record!",
                        "%(count)d devices without record!",
                        recordless_devices_count,
                    )
                    % {"count": recordless_devices_count},
                    cta_link=cta_link,
                    cta_text=_("Add record?"),
                )
            )

        # Devices and imports without tenant: only for users of the Tenant
        # admin action that assigns them (TenantAdmin.has_assign_permission).
        if user.is_staff and user.has_perm("tenants.change_tenant"):
            devices_without_tenant = device_counts["without_tenant_count"] if user.has_perm("core.change_device") else 0
            imports_without_tenant = (
                ImporterList.objects.filter(tenant__isnull=True).count()
                if user.has_perm("dataexchange.change_importerlist")
                else 0
            )
            for count, msg in [
                (
                    devices_without_tenant,
                    ngettext(
                        "%(count)d device without tenant!",
                        "%(count)d devices without tenant!",
                        devices_without_tenant,
                    ),
                ),
                (
                    imports_without_tenant,
                    ngettext(
                        "%(count)d import without tenant!",
                        "%(count)d imports without tenant!",
                        imports_without_tenant,
                    ),
                ),
            ]:
                if count:
                    sticky_messages.append(
                        StickyMessage(
                            level=messages.WARNING,
                            msg=msg % {"count": count},
                            cta_link=reverse("admin:tenants_tenant_changelist"),
                            cta_text=_("Assign a tenant?"),
                        )
                    )

        # Only for users who work with devices at all: they would otherwise
        # just see empty lists. The link only for those who may open its page.
        if not request.tenants and user.has_perm("core.view_device"):
            no_tenant_hint = StickyMessage(
                level=messages.WARNING,
                msg=_("None of your groups belongs to a tenant, so you see no devices."),
            )
            if user.has_perm("tenants.view_tenant"):
                no_tenant_hint.cta_link = reverse("tenants:index")
                no_tenant_hint.cta_text = _("Assign groups to tenants?")
            sticky_messages.append(no_tenant_hint)

        room_flags = Room.objects.aggregate(
            room_count=Count("pk"),
            external_room_count=Count("pk", filter=Q(is_external=True)),
            auto_return_room_count=Count("pk", filter=Q(is_auto_return_room=True)),
        )

        if room_flags["room_count"]:
            if not room_flags["external_room_count"]:
                sticky_messages.append(
                    StickyMessage(
                        level=messages.WARNING,
                        msg=_("No room configured as 'is_external'!"),
                        cta_link=rooms_index_url,
                        cta_text=_("Configure one?"),
                    )
                )

            if not room_flags["auto_return_room_count"]:
                sticky_messages.append(
                    StickyMessage(
                        level=messages.WARNING,
                        msg=_("No room configured as 'is_auto_return_room'!"),
                        cta_link=rooms_index_url,
                        cta_text=_("Configure one?"),
                    )
                )

        else:
            sticky_messages.append(
                StickyMessage(
                    level=messages.WARNING,
                    msg=_("No rooms defined yet."),
                    cta_link=reverse("rooms:add"),
                    cta_text=_("Add some rooms?"),
                )
            )

        # Local import to avoid a circular import (organization -> core).
        from dlcdb.organization.models import Branding

        if not Branding.load().organization_it_dept_email:
            sticky_messages.append(
                StickyMessage(
                    level=messages.WARNING,
                    msg=_("No IT department contact email configured in Branding!"),
                    cta_link=reverse("admin:organization_branding_changelist"),
                    cta_text=_("Configure it?"),
                )
            )

    for message in sticky_messages:
        # Only add current message if not already exists in messages display
        current_messages_content = [msg.message for msg in list(messages.get_messages(request))]
        if message.get_formatted_msg() not in current_messages_content:
            messages.add_message(request, message.level, message.get_formatted_msg())

    return {}  # empty dict to make context_processor happy


def django_settings(request):
    """
    Expose some cherry picked Django settings to the templates.
    """
    return {
        "django_settings": {
            "DEFAULT_FROM_EMAIL": settings.DEFAULT_FROM_EMAIL,
        }
    }
