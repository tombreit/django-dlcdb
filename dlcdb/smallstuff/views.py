# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

# from datetime import datetime

from django.shortcuts import render
from django.utils.timezone import now
from django.utils import timezone
from django.http import HttpResponse

from dlcdb.core.models import Person

from .models import AssignedThing
from .filters import PersonFilter
from .forms import AssignedThingsForm


def person_search(request):
    # query = request.GET.get("q")
    filter = PersonFilter(request.POST)
    template = "smallstuff/person_search.html"
    context = {"filter": filter}

    if request.htmx:
        template = "smallstuff/person_search_results.html"

    return render(request, template, context)


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
    }
    return render(request, template, context)


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


def remove_assignement(request, assignment_id):
    print(f"{now()=}")
    print(f"{timezone.localtime(timezone.now())=}")
    to_unassign_assignment = AssignedThing.currently_assigned_objects.get(id=assignment_id)
    to_unassign_assignment.unassigned_at = timezone.localtime(timezone.now())  # datetime.now()
    to_unassign_assignment.unassigned_by = request.user

    to_unassign_assignment.save()  # update_fields=['unassigned_at', 'unassigned_by']

    response = HttpResponse(status=204)
    response["HX-Trigger"] = "newAssignment"
    return response


def add_assignement(request, person_id):
    if request.method == "POST":
        print("add_assignement POST")
        form = AssignedThingsForm(request.POST)
        if form.is_valid():
            # print(f"{form.cleaned_data=}")
            form.instance.assigned_at = timezone.localtime(timezone.now())
            form.instance.assigned_by = request.user
            form.save()
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "newAssignment"
            return response

    else:
        print("add_assignement GET")

        person = Person.objects.get(id=person_id)
        form = AssignedThingsForm(initial={"person": person})

        template = "smallstuff/includes/add_assignement.html"
        context = {"person": person, "form": form}
        return render(request, template, context)
