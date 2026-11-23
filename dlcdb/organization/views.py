# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.contrib.auth.decorators import login_not_required
from django.db.models import Count, Q
from django.http import FileResponse, HttpRequest
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from dlcdb.core.models import OrganizationalPosition, OrganizationalUnit
from dlcdb.core.utils.htmx import htmx_permission_required
from dlcdb.theme.settings_page import settings_page
from dlcdb.theme.viewsets import Column, ModelViewSet, Usage

from .forms import BrandingForm, OrganizationalPositionForm, OrganizationalUnitForm


@login_not_required  # the login page shows it too
@require_GET
@cache_control(max_age=60 * 60 * 24, immutable=True, public=True)  # one day
def favicon(request: HttpRequest) -> FileResponse:
    file = settings.BASE_DIR / "dlcdb" / "theme" / "static" / "theme" / "branding" / "favicon.ico"

    return FileResponse(file.open("rb"))


@htmx_permission_required("organization.view_branding")
def branding(request):
    """Settings › Organization: the organisation's names, address, IT contact, logos and room plan."""
    return settings_page(request, BrandingForm, icon="bi-building", template="organization/branding.html")


class NameViewSet(ModelViewSet):
    """
    Units and positions: a name that persons hold. Global, like device types: no
    tenant scoping. The lists count the active persons, as the persons list does.
    """

    list_display = [
        "name",
        Column(
            "persons_count",
            _("Persons"),
            sort_key="persons_count",
            classname="text-end",
            cell_template_name="theme/viewsets/cells/_count.html",
        ),
    ]
    search_fields = ["name"]
    ordering = "name"
    # From the model to its persons.
    persons_lookup = ""

    def get_queryset(self):
        active = Q(**{f"{self.persons_lookup}__deleted_at__isnull": True})
        return self.model.objects.annotate(persons_count=Count(self.persons_lookup, filter=active))


def _persons_usage(persons_filter):
    """The edit page's card: the active persons, linked to the persons list filtered by the entry."""
    return Usage(_("Persons"), "persons_count", "persons:index", persons_filter, "core.view_person", icon="bi-people")


class UnitViewSet(NameViewSet):
    model = OrganizationalUnit
    form_class = OrganizationalUnitForm
    icon = "bi-diagram-3"
    url_namespace = "unit"
    # Person.organizational_unit has no related_name.
    persons_lookup = "person"
    usage = _persons_usage("organizational_unit")


class PositionViewSet(NameViewSet):
    model = OrganizationalPosition
    form_class = OrganizationalPositionForm
    icon = "bi-person-badge"
    url_namespace = "position"
    persons_lookup = "persons"
    usage = _persons_usage("organizational_positions")
