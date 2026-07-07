# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from dlcdb.core.models import Person

from .forms import ReportSubscriptionForm
from .models import Subscription
from .reports import create_report_message
from .tasks import send_message


def _get_person(request):
    """The Person matching the logged-in user; there is no FK, only email."""
    return Person.objects.filter(email=request.user.email).first()


def _get_own_report_subscription(request, pk):
    return get_object_or_404(
        Subscription,
        pk=pk,
        subscriber=_get_person(request),
        event__in=Subscription.REPORT_EVENTS,
    )


@login_required
def index(request):
    person = _get_person(request)

    form = None
    if person:
        instance = Subscription(subscriber=person)
        if request.method == "POST":
            form = ReportSubscriptionForm(request.POST, instance=instance)
            if form.is_valid():
                form.save()
                messages.success(request, _("Subscription added."))
                return redirect("notifications:index")
        else:
            form = ReportSubscriptionForm(instance=instance)

    subscriptions = (
        Subscription.objects.filter(subscriber=person).select_related("device").order_by("-subscribed_at")
        if person
        else Subscription.objects.none()
    )

    context = {
        "person": person,
        "subscriptions": subscriptions,
        "form": form,
    }
    return TemplateResponse(request, "notifications/index.html", context)


@login_required
@require_POST
def delete(request, pk):
    subscription = _get_own_report_subscription(request, pk)
    subscription.delete()
    messages.success(request, _("Subscription deleted."))
    return redirect("notifications:index")


@login_required
@require_POST
def trigger(request, pk):
    """Create and immediately send a report, without shifting the reporting window."""
    subscription = _get_own_report_subscription(request, pk)
    message = create_report_message(subscription, update_window=False)
    if message and send_message.call_local(message.id):
        messages.success(request, _("Report has been sent via email."))
    else:
        messages.warning(request, _("No report sent."))
    return redirect("notifications:index")


@login_required
@require_POST
def toggle(request, pk):
    subscription = _get_own_report_subscription(request, pk)
    subscription.is_active = not subscription.is_active
    subscription.save()
    if subscription.is_active:
        messages.success(request, _("Subscription activated."))
    else:
        messages.success(request, _("Subscription deactivated."))
    return redirect("notifications:index")
