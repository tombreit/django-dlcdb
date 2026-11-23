# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
The lending profiles: one per device type, with the lending slip template, the
preparation checklist and the regulations; and the regulations themselves
(core.Link), a link or a file the borrower confirms on the slip. Both are a
ModelViewSet (theme/viewsets.py) under Settings, global like device types: no
tenant scoping.
"""

from django.contrib import messages
from django.db.models import Count
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from dlcdb.core.models import Link
from dlcdb.theme.viewsets import Column, CreateView, EditView, HistoryView, ModelViewSet

from .forms import LendingProfileForm, LinkForm
from .models import LendingProfile
from .starter import restore_empty

PRESENT = "theme/viewsets/cells/_present.html"


def _restore_starter_content(request, form):
    """An emptied slip template or checklist gets the starter content again, and the user is told."""
    for field in restore_empty(form.instance):
        messages.info(request, _("“%(field)s” was empty and holds the starter content again.") % {"field": field})


class ProfileCreateView(CreateView):
    def form_valid(self, form):
        _restore_starter_content(self.request, form)
        return super().form_valid(form)


class ProfileEditView(EditView):
    def form_valid(self, form):
        _restore_starter_content(self.request, form)
        return super().form_valid(form)


class LendingProfileViewSet(ModelViewSet):
    model = LendingProfile
    form_class = LendingProfileForm
    form_fields_template = "lending/includes/_profile_fields.html"
    icon = "bi-card-checklist"
    url_namespace = "profile"
    list_display = [
        Column("device_type", gettext_lazy("Device type"), sort_key="device_type__name"),
        Column(
            "lent_sheet_template", gettext_lazy("Slip template"), classname="text-center", cell_template_name=PRESENT
        ),
        Column(
            "lending_preparation_checklist",
            gettext_lazy("Checklist"),
            classname="text-center",
            cell_template_name=PRESENT,
        ),
    ]
    search_fields = ["device_type__name"]
    ordering = "device_type__name"
    add_view_class = ProfileCreateView
    edit_view_class = ProfileEditView
    history_view_class = HistoryView

    def get_queryset(self):
        return LendingProfile.objects.select_related("device_type")


class RegulationViewSet(ModelViewSet):
    """
    The regulations. A file is public under /media/links/, as the slips print
    its address: adding and changing are sensitive permissions (accounts.permissions).
    """

    model = Link
    form_class = LinkForm
    icon = "bi-file-earmark-text"
    url_namespace = "regulation"
    list_display = [
        Column("linktext", gettext_lazy("Link text"), sort_key="linktext"),
        Column("url", gettext_lazy("URL"), classname="text-center", cell_template_name=PRESENT),
        Column("file", gettext_lazy("File"), classname="text-center", cell_template_name=PRESENT),
        Column(
            "profiles",
            gettext_lazy("Lending profiles"),
            sort_key="profiles",
            classname="text-end",
            cell_template_name="theme/viewsets/cells/_count.html",
        ),
    ]
    search_fields = ["linktext", "url"]
    ordering = "linktext"

    def get_queryset(self):
        return Link.objects.annotate(profiles=Count("lendingprofileregulation"))
