# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from operator import itemgetter
from importlib import import_module
from dataclasses import dataclass
from django.contrib import messages
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.utils.html import format_html
from django.urls import reverse
from django.conf import settings

from dlcdb.core.models import Room, Device
from dlcdb.core.utils.tenants import tenant_scoped_queryset


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

        qs = tenant_scoped_queryset(Device.objects.all(), request, tenant_field="tenant")
        recordless_devices = qs.filter(active_record__isnull=True)
        recordless_devices_count = recordless_devices.count()

        if recordless_devices_count:
            if recordless_devices_count == 1:
                # A single device: jump straight into Move with it preselected.
                cta_link = f"{reverse('assets:relocate')}?device={recordless_devices.first().pk}"
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
                    cta_text=_("Add proper record?"),
                )
            )

        if Room.objects.exists():
            if not Room.objects.filter(is_external=True).exists():
                sticky_messages.append(
                    StickyMessage(
                        level=messages.WARNING,
                        msg=_("No room configured as 'is_external'!"),
                        cta_link=rooms_index_url,
                        cta_text=_("Configure one?"),
                    )
                )

            if not Room.objects.filter(is_auto_return_room=True).exists():
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

    for message in sticky_messages:
        # Only add current message if not already exists in messages display
        current_messages_content = [msg.message for msg in list(messages.get_messages(request))]
        if message.get_formatted_msg() not in current_messages_content:
            messages.add_message(request, message.level, message.get_formatted_msg())

    return {}  # empty dict to make context_processor happy


def _app_navigation(app_name):
    """Import an app's ``navigation`` module (single source of nav declarations).

    ``app_name`` is the full dotted path, e.g. "dlcdb.inventory". Apps without a
    navigation module simply contribute nothing. ModuleNotFoundError (not bare
    ImportError) is caught so a genuine import error inside a navigation.py still
    surfaces instead of being silently swallowed.
    """
    try:
        return import_module(f"{app_name}.navigation")
    except ModuleNotFoundError:
        return None


# https://github.com/apache/airavata-django-portal/blob/0e2736ba1e72d24fa47b1699a11cbda4dc3fcc4c/django_airavata/context_processors.py#L99
def nav(request):
    nav_items = []
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
        raise NotImplementedError(
            "Function _get_is_active to retrieve the active navigation entry is not implemented (yet)."
        )

    def _get_has_permission(user, permission):
        if not user or not permission:
            return False

        if permission == "true":
            # The string "true" disables *model-permission* checking but still
            # requires an authenticated user (matches @login_required on such
            # views, e.g. licenses:index).
            return user.is_authenticated

        if "." not in permission:
            # One authoritative scheme: a nav entry's required_permission must be
            # the Django-canonical "app_label.codename" (what user.has_perm expects).
            # A bare codename is ambiguous — it silently meant a different permission
            # depending on which app's navigation.py it lived in — so reject it loudly
            # instead of guessing an app label.
            raise ImproperlyConfigured(f"nav required_permission {permission!r} must be 'app_label.codename'")

        return permission in user.get_all_permissions()

    # Namespace of the currently resolved view, used to mark the matching nav
    # entry as "active" (e.g. on /lending/* the "Lending" entry is highlighted).
    resolver_match = getattr(request, "resolver_match", None)
    current_app_namespace = (resolver_match.namespace or resolver_match.app_name) if resolver_match else None
    current_url_name = resolver_match.url_name if resolver_match else None

    for app in dlcdb_apps:
        # print(f"{app}: name: {app.name}; verbose_name: {app.verbose_name}; label: {app.label}")

        nav_module = _app_navigation(app.name)
        if nav_module is None:
            continue

        for nav_entry in getattr(nav_module, "nav_entries", []):
            # name: dlcdb.reporting; verbose_name: DLCDB Reporting; label: reporting
            # for a concrete permission string we need the app name without the project prefix
            # so 'app.label' seems to fit
            required_permission = nav_entry.get("required_permission")
            has_permission = _get_has_permission(request.user, required_permission)

            # Ugly hack to conditionally hide some nav_entries
            show_condition = nav_entry.get("show_condition")
            if show_condition:
                if show_condition == "active_inventory_exists":
                    from dlcdb.core.models.inventory import Inventory

                    active_inventory_exists = Inventory.objects.active_inventory()
                    if not active_inventory_exists:
                        continue

            if has_permission or request.user.is_superuser:
                url = nav_entry.get("url") or ""
                url_namespace = url.rsplit(":", 1)[0] if ":" in url else ""
                in_namespace = bool(current_app_namespace) and url_namespace == current_app_namespace

                # Most apps have exactly one nav entry per namespace, so any page
                # in that namespace should highlight it. An app with more than one
                # entry sharing a namespace (e.g. assets: "Devices" vs "Move") must
                # list its own url_names in "active_url_names" to disambiguate.
                active_url_names = nav_entry.get("active_url_names")
                is_active = in_namespace and (active_url_names is None or current_url_name in active_url_names)

                nav_item = {
                    "label": nav_entry.get("label"),
                    "icon": nav_entry.get("icon"),
                    "url": nav_entry.get("url"),
                    "slot": nav_entry.get("slot"),
                    "order": nav_entry.get("order"),
                    "active": is_active,
                }
                nav_items.append(nav_item)

    nav_items = sorted(nav_items, key=itemgetter("order"))

    # Focus config for the current app (its navigation.nav_focus). Deliberately
    # NOT run through the permission gate: these are per-app helper links shown
    # only while already inside that app (matches previous behavior).
    nav_focus = {}
    if current_app_namespace:
        try:
            current_app = apps.get_app_config(current_app_namespace)
        except LookupError:
            current_app = None
        if current_app is not None:
            module = _app_navigation(current_app.name)
            if module is not None:
                nav_focus = getattr(module, "nav_focus", {}) or {}

    return {
        "nav_items_main": [item for item in nav_items if item["slot"] == "nav_main"],
        "nav_items_masterdata": [item for item in nav_items if item["slot"] == "nav_masterdata"],
        "nav_items_processes": [item for item in nav_items if item["slot"] == "nav_processes"],
        "nav_items_settings": [item for item in nav_items if item["slot"] == "nav_settings"],
        "nav_focus": nav_focus,
    }


def django_settings(request):
    """
    Expose some cherry picked Django settings to the templates.
    """
    return {
        "django_settings": {
            "DEFAULT_FROM_EMAIL": settings.DEFAULT_FROM_EMAIL,
        }
    }
