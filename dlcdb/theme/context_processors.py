# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from importlib import import_module
from operator import itemgetter

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from dlcdb import __version__
from dlcdb.core.models.inventory import get_active_inventory

# Kept in step with [project.urls] in pyproject.toml.
REPOSITORY_URL = "https://github.com/tombreit/django-dlcdb"
ISSUES_URL = "https://gitlab.gwdg.de/t.breitner/django-dlcdb/-/issues"


def project_meta(request):
    """Expose project version and source/issue URLs (used by the theme footer)."""
    return {
        "project_version": __version__,
        "project_repository_url": REPOSITORY_URL,
        "project_issues_url": ISSUES_URL,
    }


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

        if isinstance(permission, (list, tuple)):
            # Several permissions, any one of which reveals the entry. Needed for
            # menus that front more than one lifecycle move: "Move" serves locate,
            # relocate and find, so requiring a single permission would hide it
            # from users who legitimately hold one of the others.
            return any(_get_has_permission(user, entry) for entry in permission)

        if "." not in permission:
            # One authoritative scheme: a nav entry's required_permission must be
            # the Django-canonical "app_label.codename" (what user.has_perm expects).
            # A bare codename is ambiguous — it silently meant a different permission
            # depending on which app's navigation.py it lived in — so reject it loudly
            # instead of guessing an app label.
            raise ImproperlyConfigured(f"nav required_permission {permission!r} must be 'app_label.codename'")

        return user.has_perm(permission)

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
            # name: dlcdb.reporting; verbose_name: Reporting; label: reporting
            # for a concrete permission string we need the app name without the project prefix
            # so 'app.label' seems to fit
            required_permission = nav_entry.get("required_permission")
            has_permission = _get_has_permission(request.user, required_permission)

            if has_permission:
                # Ugly hack to conditionally hide some nav_entries. Checked only
                # after the permission gate so unpermitted users never trigger
                # the underlying query.
                show_condition = nav_entry.get("show_condition")
                if show_condition == "active_inventory_exists":
                    if not get_active_inventory(request):
                        continue

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
