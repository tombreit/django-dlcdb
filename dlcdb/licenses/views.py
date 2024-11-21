from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse

from dlcdb.core.models import LicenceRecord


@login_required
def index(request):
    licenses = LicenceRecord.objects.all()
    print(f"{licenses=}")

    context = {
        "licenses": licenses,
    }

    return TemplateResponse(request, "licenses/index.html", context)


@login_required
def new(request):
    return TemplateResponse(request, "", {})


@login_required
def edit(request):
    return TemplateResponse(request, "", {})
