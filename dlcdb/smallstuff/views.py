# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

# from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from dlcdb.core.models import Person
from dlcdb.core.utils.htmx import htmx_permission_required

from .filters import PersonFilter
from .forms import AssignedThingsForm
from .models import AssignedThing


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


@htmx_permission_required("smallstuff.change_assignedthing")
def remove_assignement(request, assignment_id):
    to_unassign_assignment = AssignedThing.currently_assigned_objects.get(id=assignment_id)
    to_unassign_assignment.unassigned_at = timezone.localtime(timezone.now())  # datetime.now()
    to_unassign_assignment.unassigned_by = request.user

    to_unassign_assignment.save()  # update_fields=['unassigned_at', 'unassigned_by']

    response = HttpResponse(status=204)
    response["HX-Trigger"] = "newAssignment"
    return response


@htmx_permission_required("smallstuff.add_assignedthing")
def add_assignement(request, person_id):
    if request.method == "POST":
        form = AssignedThingsForm(request.POST)
        if form.is_valid():
            form.instance.assigned_at = timezone.localtime(timezone.now())
            form.instance.assigned_by = request.user
            form.save()

            # Reload the form for the next assignment
            person = Person.objects.get(id=person_id)
            context = {
                "person": person,
                "form": AssignedThingsForm(initial={"person": person}),
            }
            response = render(request, "smallstuff/includes/add_assignement.html", context)
            response["HX-Trigger"] = "newAssignment"

            return response

    else:
        person = Person.objects.get(id=person_id)
        form = AssignedThingsForm(initial={"person": person})

        template = "smallstuff/includes/add_assignement.html"
        context = {"person": person, "form": form}
        return render(request, template, context)
