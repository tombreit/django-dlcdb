from django import forms
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
# from django.core.validators import validate_email

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, HTML
from crispy_bootstrap5.bootstrap5 import FloatingField

from dlcdb.core.models import Device, DeviceType, Person
from .subscribers import manage_subscribers


class LicenseForm(forms.ModelForm):
    contract_termination = forms.BooleanField(
        required=False,
        # The initial value will be set in the __init__ method
        help_text=_("Check this box if the contract has been terminated."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if this is an edit form (instance exists)
        self.is_edit = self.instance and self.instance.pk is not None

        # Limit device-type choices to "License-type" choices
        self.fields["device_type"].queryset = DeviceType.objects.filter(
            Q(name__startswith="Lizenz::") | Q(name__startswith="License::") | Q(name__startswith="Licence::")
        )
        # Set initial value for contract_termination checkbox
        self.fields["contract_termination"].initial = bool(self.instance.contract_termination_date)

        # Dynamically set initial subscribers
        # if self.is_edit:
        #     current_subscribers = self.instance.subscription_set.values_list("subscriber_id", flat=True)
        #     self.fields["subscribers"].initial = current_subscribers

        # Reset queryset each time to avoid caching
        self.fields["subscribers"] = forms.ModelMultipleChoiceField(
            queryset=Person.objects.filter(email__isnull=False),
            required=False,
            help_text=_("Select one or more subscribers."),
            widget=forms.SelectMultiple(
                attrs={
                    "class": "is-tom-select",
                    # "data-placeholder": "-----",
                }
            ),
            initial=self.instance.subscription_set.values_list("subscriber_id", flat=True)
            if self.instance.pk
            else None,
        )

        # Crispy forms
        self.helper = FormHelper()
        self.helper.form_tag = False

        self.helper.layout = Layout(
            Row(
                Column("sap_id", css_class="col-md-4"),
                Column("subscribers", css_class="col-md-8"),
            ),
            Div(HTML("<hr>")),
            Row(
                Column(FloatingField("manufacturer"), css_class="col-md-4"),
                Column(FloatingField("series"), css_class="col-md-6"),
            ),
            Row(
                Column(FloatingField("supplier"), css_class="col-md-4"),
                Column(FloatingField("order_number"), css_class="col-md-3"),
                Column(FloatingField("device_type"), css_class="col-md-3"),
            ),
            Div(
                Row(
                    Column(FloatingField("contract_start_date"), css_class="col-md-3"),
                    Column(FloatingField("contract_expiration_date"), css_class="col-md-3"),
                    # The field "contract_termination" is only shown in edit mode:
                    Column("contract_termination", css_class="col-md-3 offset-md-3") if self.is_edit else None,
                ),
                css_class="alert alert-info",
            ),
            Row(
                Column(FloatingField("note"), css_class="col-md-6"),
                Column(FloatingField("procurement_note"), css_class="col-md-6"),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        if not any(cleaned_data.values()):
            raise ValidationError(_("At least one field must be filled."))

    def save(self, commit=True):
        instance = super().save(commit=False)

        # The database field is a DateTimeField, so we cast the BoolenField to
        # a DateTimeField.
        if self.cleaned_data.get("contract_termination"):
            instance.contract_termination_date = timezone.now()
        else:
            instance.contract_termination_date = None

        instance.save()
        self.save_m2m()

        subscribers = self.cleaned_data.get("subscribers")
        manage_subscribers(instance, subscribers)

        return instance

    class Meta:
        model = Device
        fields = [
            "sap_id",
            "supplier",
            "order_number",
            "book_value",
            "manufacturer",
            "series",
            "contract_start_date",
            "contract_expiration_date",
            "procurement_note",
            "note",
            "device_type",
            "contract_termination",
        ]
        labels = {
            "subscribers": _("Subscribers"),
            "device_type": _("Type"),
            "series": _("Name"),
            "contract_start_date": _("Start Date"),
            "contract_expiration_date": _("Expiration Date"),
        }
        widgets = {
            # Must set the date format, otherwise the date input field
            # is not populated from the model instance.
            "contract_expiration_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "contract_start_date": forms.DateInput(format=("%Y-%m-%d"), attrs={"type": "date"}),
            "note": forms.Textarea(attrs={"rows": 6, "style": "resize: vertical; height: 10em;"}),
            "procurement_note": forms.Textarea(attrs={"rows": 6, "style": "resize: vertical; height: 10em;"}),
        }
