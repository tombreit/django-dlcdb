from operator import itemgetter
from dataclasses import dataclass
from django.contrib import messages
from django.apps import apps
from django.utils.translation import gettext as _
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import pluralize

from dlcdb.core.models import Room, Device


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

        # Make this queryset tenant aware
        qs = Device.objects.none()

        if request.user.is_superuser:
            # No pre-filtering for superusers
            qs = Device.objects.all()
        elif request.tenant:
            qs = qs.filter(tenant=request.tenant)

        if qs.filter(active_record__isnull=True).exists():
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
        # Only add current message if not already exists in messages display
        current_messages_content = [msg.message for msg in list(messages.get_messages(request))]
        if message.get_formatted_msg() not in current_messages_content:
            messages.add_message(request, message.level, message.get_formatted_msg())

    return {}  # empty dict to make context_processor happy


# https://github.com/apache/airavata-django-portal/blob/0e2736ba1e72d24fa47b1699a11cbda4dc3fcc4c/django_airavata/context_processors.py#L99
def nav(request):
    nav_items =[]
    dlcdb_apps = [app for app in apps.get_app_configs()]

    def _get_is_active():
        #     # convert "/djangoapp/path/in/app" to "path/in/app"
        #     app_path = "/".join(request.path.split("/")[2:])
        #     for nav_item in nav:
        #         if 'active_prefixes' in nav_item:
        #             if re.match("|".join(nav_item['active_prefixes']), app_path):
        #                 nav_item['active'] = True
        #             else:
        #                 nav_item['active'] = False
        #         else:
        #             # 'active_prefixes' is optional, and if not specified, assume
        #             # current item is active
        #             nav_item['active'] = True
        raise NotImplementedError("Function _get_is_active to retrieve the active navigation entry is not implemented (yet).")

    def _get_has_permission(user, applabel, permission):
        if not all([user, applabel, permission]):
            return False

        if permission == "true":
            # The string "true" is currently used to disable permission checking
            return True

        requested_permission = f"{applabel}.{permission}"
        user_permissions = user.get_all_permissions()
        # print(user_permissions)
        return requested_permission in user_permissions

    for app in dlcdb_apps:
        # print(f"{app}: name: {app.name}; verbose_name: {app.verbose_name}; label: {app.label}")

        if not hasattr(app, "nav_entries"):
            continue

        for nav_entry in app.nav_entries:
            # name: dlcdb.reporting; verbose_name: DLCDB Reporting; label: reporting
            # for a concrete permission string we need the app name without the project prefix
            # so 'app.label' seems to fit
            app_label = app.label
            required_permission = nav_entry.get("required_permission")
            has_permission = _get_has_permission(request.user, app_label, required_permission)

            if has_permission:
                nav_item = {
                    "label": nav_entry.get("label"),
                    "icon": nav_entry.get("icon"),
                    "url": nav_entry.get("url"),
                    "slot": nav_entry.get("slot"),
                    "order": nav_entry.get("order"),
                }
                nav_items.append(nav_item)

    nav_items = sorted(nav_items, key=itemgetter('order'))
    return {"nav_items": nav_items}
