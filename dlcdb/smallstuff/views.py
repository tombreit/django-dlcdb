# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

# from datetime import datetime

from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from dlcdb.core.models import Person
from dlcdb.core.utils.htmx import htmx_permission_required
from dlcdb.theme.viewsets import Column, EditView, ModelViewSet

from .filters import PersonFilter
from .forms import AssignedThingsForm, ThingForm
from .models import AssignedThing, Thing


@htmx_permission_required("smallstuff.view_assignedthing")
def person_search(request):
    # query = request.GET.get("q")
    # Start from an empty queryset: django-filter skips empty filter values, so
    # a blank search box must yield no people rather than the whole directory.
    filter = PersonFilter(request.POST, queryset=Person.objects.none())
    template = "smallstuff/person_search.html"
    context = {"filter": filter}

    if request.htmx:
        template = "smallstuff/person_search_results.html"

    return render(request, template, context)


@htmx_permission_required("smallstuff.view_assignedthing")
def person_detail(request, person_id):
    try:
        person = Person.smallstuff_person_objects.get(id=person_id)
        assignments = AssignedThing.currently_assigned_objects.filter(person=person)
    except Person.DoesNotExist:
        person = None
        assignments = None

    template = "smallstuff/person_detail.html"
    context = {
        "person": person,
        "assignments": assignments,
        "can_add": request.user.has_perm("smallstuff.add_assignedthing"),
    }
    return render(request, template, context)


@htmx_permission_required("smallstuff.view_assignedthing")
def get_assignements(request, person_id, state):
    if state == "issued":
        assignments = AssignedThing.currently_assigned_objects.filter(person=person_id)
    elif state == "returned":
        assignments = AssignedThing.objects.filter(person=person_id, unassigned_at__isnull=False)

    template = "smallstuff/includes/assignements.html"
    context = {
        "assignments": assignments,
    }
    return render(request, template, context)


@require_POST
@htmx_permission_required("smallstuff.change_assignedthing")
def remove_assignement(request, assignment_id):
    """Take a thing back. One returned meanwhile (in another tab, say) stays as it was; the list reloads."""
    assignment = get_object_or_404(AssignedThing, id=assignment_id)
    if assignment.unassigned_at is None:
        assignment.unassigned_at = timezone.now()
        assignment.unassigned_by = request.user
        assignment.save(update_fields=["unassigned_at", "unassigned_by"])

    response = HttpResponse(status=204)
    response["HX-Trigger"] = "newAssignment"
    return response


@htmx_permission_required("smallstuff.add_assignedthing")
def add_assignement(request, person_id):
    """The form to hand out a thing; a refused POST comes back with its errors."""
    person = get_object_or_404(Person, id=person_id)
    form = AssignedThingsForm(request.POST or None, initial={"person": person})
    template = "smallstuff/includes/add_assignement.html"

    if request.method == "POST" and form.is_valid():
        form.instance.assigned_at = timezone.now()
        form.instance.assigned_by = request.user
        form.save()
        # A fresh form for the next thing; the list reloads.
        response = render(request, template, {"person": person, "form": AssignedThingsForm(initial={"person": person})})
        response["HX-Trigger"] = "newAssignment"
        return response

    return render(request, template, {"person": person, "form": form})


class ThingEditView(EditView):
    """A thing's page also lists who holds it now."""

    def get_context_data(self, **kwargs):
        holders = AssignedThing.currently_assigned_objects.filter(thing=self.object).select_related("person")
        return super().get_context_data(holders=holders, **kwargs)


class ThingViewSet(ModelViewSet):
    """The catalogue of things that can be handed out (Settings › Smallstuff catalogue)."""

    model = Thing
    form_class = ThingForm
    icon = "bi-handbag"
    list_display = ["name", Column("issued", _("Issued"), sort_key="issued", classname="text-end")]
    search_fields = ["name"]
    ordering = "name"
    edit_view_class = ThingEditView
    edit_template_name = "smallstuff/thing_edit.html"

    def get_queryset(self):
        # Ordered by the index: a counting query ignores Meta.ordering.
        return Thing.objects.annotate(
            issued=Count("assignedthing", filter=Q(assignedthing__unassigned_at__isnull=True))
        )
