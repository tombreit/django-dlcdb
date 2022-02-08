from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

from dlcdb.core.models import Person, Device, Room
from .filters import PersonFilter
from .forms import LendingForm


@require_http_methods(["GET"])
def person_search(request):
    query = request.GET.get("q")
    filter = PersonFilter(request.GET)
    template = "lending/person_list.html"
    context = {'filter': filter}

    print(f"{request.htmx=}")
    if request.htmx:
        template = "lending/htmx/htmx_person_list.html"

    return render(request, template, context)


def person_detail(request, person_id):
    person = Person.objects.get(id=person_id)
    lendings = Device.objects.filter(active_record__person=person)
    template = "lending/detail_view.html"
    form = LendingForm()
    context = {
        "person": person,
        "lendings": lendings,
        "form": form,
    }
    return render(request, template, context)


# @require_http_methods(["POST"])
# @require_POST
def add_lending(request, person_id):
    template = "lending/add_lending.html"
    person = Person.objects.get(id=person_id)
    default_room = Room.objects.get(is_external=True)

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        print(f"add_lending POST")

        # create a form instance and populate it with data from the request:
        form = LendingForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            print(f"form.is_valid()!")
            # process the data in form.cleaned_data as required
            print(f"{form.cleaned_data=}")
            return redirect('lending:person_detail', person_id)

    # if a GET (or any other method) we'll create a blank form
    else:
        print(f"add_lending GET")
        form = LendingForm(
            initial={
                'person': person,
                'room': default_room,
            }
        )

    return render(request, template, {'form': form})