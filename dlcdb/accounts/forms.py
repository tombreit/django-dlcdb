# SPDX-FileCopyrightText: 2025 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AdminUserCreationForm, AuthenticationForm
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from dlcdb.tenants.models import Tenant
from dlcdb.theme.forms import add_bootstrap_classes
from dlcdb.theme.widgets import FilteredSelectMultipleWidget

from .models import CustomUser, is_ldap_mirrored


def _change_group():
    return Permission.objects.get(content_type__app_label="accounts", codename="change_group")


def may_still_change_groups(editor, *, without):
    """
    Whether ``editor`` may change groups through anything but the group
    ``without``: no locking oneself out by editing or deleting that group.
    """
    if editor.is_superuser:
        return True
    change_group = _change_group()
    if editor.user_permissions.contains(change_group):
        return True
    return editor.groups.exclude(pk=without.pk).filter(permissions=change_group).exists()


def _members_field():
    """Only active users: deactivated members stay members, unseen."""
    return forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by("email"),
        required=False,
        label=_("Members"),
        widget=FilteredSelectMultipleWidget(available_label=_("Users"), chosen_label=_("Members")),
    )


class GroupForm(forms.ModelForm):
    """
    A group's name, its permissions among DLCDB's own, its active members and its
    tenants; a new group's too (``instance=Group()``). What the form doesn't show
    stays as it is: the permissions no page of DLCDB checks, and deactivated
    members.

    ``own`` is ``permissions.own_permissions()``, ``editor`` the user saving.
    Members need ``accounts.view_customuser`` to be shown and
    ``accounts.change_customuser`` to be changed; tenants need
    ``tenants.change_tenant``. LDAP sets a mirrored group's members and matches
    it by name: both are read-only.
    """

    permissions = forms.ModelMultipleChoiceField(queryset=Permission.objects.none(), required=False)
    members = _members_field()
    tenants = forms.ModelMultipleChoiceField(queryset=Tenant.objects.order_by("name"), required=False)

    class Meta:
        model = Group
        fields = ["name"]

    class Media:
        # The group profiles' buttons tick their permissions.
        js = ["accounts/js/group-profiles.js"]

    def __init__(self, *args, own, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.own, self.editor = own, editor
        saved = self.instance.pk is not None
        ldap = saved and is_ldap_mirrored(self.instance)

        self.fields["permissions"].queryset = Permission.objects.filter(pk__in=[p.permission.pk for p in own])
        self.initial["permissions"] = (
            list(self.instance.permissions.filter(pk__in=self.fields["permissions"].queryset)) if saved else []
        )
        if ldap:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = _("LDAP finds this group by its name, so it keeps it.")
        elif not saved and getattr(settings, "AUTH_LDAP_MIRROR_GROUPS", None):
            self.fields["name"].help_text = _(
                "For an LDAP group, its exact name: LDAP then sets its members at their next login."
            )

        may_change_members = editor.has_perm("accounts.change_customuser")
        # A new group's members are shown only to whoever may set them: there are none to see.
        if not editor.has_perm("accounts.view_customuser") or not (saved or may_change_members):
            del self.fields["members"]
        else:
            self.initial["members"] = list(self.instance.user_set.filter(is_active=True)) if saved else []
            self.fields["members"].disabled = ldap or not may_change_members

        if not editor.has_perm("tenants.change_tenant"):
            del self.fields["tenants"]
        else:
            self.initial["tenants"] = list(self.instance.tenant_set.all()) if saved else []
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        permissions = set(cleaned_data.get("permissions", ()))
        # Add, change and delete need the model's view permission: granted along with them.
        permissions |= {p.requires for p in self.own if p.requires and p.permission in permissions}
        cleaned_data["permissions"] = permissions

        if self.instance.pk and not self._editor_keeps_change_group(permissions, cleaned_data.get("members")):
            raise ValidationError(
                _(
                    "You would lose the permission to change groups. Keep it in this group, or get it "
                    "through another group first."
                )
            )
        return cleaned_data

    def checked(self, name):
        """The values of ``name`` ticked on the page: as just submitted, or as saved."""
        if self.is_bound:
            return set(getattr(self, "cleaned_data", {}).get(name, ()))
        return set(self.initial[name])

    def save(self):
        group = super().save()
        others = list(group.permissions.exclude(pk__in=self.fields["permissions"].queryset))
        group.permissions.set([*others, *self.cleaned_data["permissions"]])
        if "members" in self.fields and not self.fields["members"].disabled:
            deactivated = list(group.user_set.filter(is_active=False))
            group.user_set.set([*deactivated, *self.cleaned_data["members"]])
        if "tenants" in self.fields and not self.fields["tenants"].disabled:
            # Saved like ticks in the tenant matrix: stamped, into each tenant's history.
            ticked = set(self.cleaned_data["tenants"])
            for tenant in ticked.symmetric_difference(self.initial["tenants"]):
                tenant.set_visible_to(group, tenant in ticked, user=self.editor)
        return group

    def _editor_keeps_change_group(self, permissions, members):
        """After the save, the editor may still change groups: through this group, or another way."""
        stays = self.editor in members if members is not None else self.instance.user_set.contains(self.editor)
        return (stays and _change_group() in permissions) or may_still_change_groups(self.editor, without=self.instance)


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "username"}))

    class Media:
        js = ["accounts/js/password-toggle.js"]


class CustomUserCreationForm(AdminUserCreationForm):
    """
    Users log in with their email address, so the admin asks for it instead of a
    username. The username follows the email, as with LDAP and EmailModelBackend.
    """

    class Meta:
        model = CustomUser
        fields = ("email",)

    def clean_email(self):
        # Like Django's UserCreationForm.clean_username: the LDAP backend looks
        # users up by email__iexact, so emails must not differ only in case.
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise self.instance.unique_error_message(CustomUser, ["email"])
        return email

    def save(self, commit=True):
        self.instance.username = self.instance.email
        return super().save(commit)


class NewUserForm(CustomUserCreationForm):
    """
    A new account in the frontend: email, name, an initial password or none
    (LDAP), and its groups. The groups need ``accounts.change_customuser``, like
    a group's members.
    """

    class Meta(CustomUserCreationForm.Meta):
        fields = ("email", "first_name", "last_name", "groups")
        widgets = {"groups": forms.CheckboxSelectMultiple}

    def __init__(self, *args, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.order_by("name")
        self.fields["groups"].help_text = ""
        if getattr(settings, "AUTH_LDAP_SERVER_URI", None):
            # With LDAP, accounts usually log in with their LDAP password.
            self.fields["usable_password"].initial = "false"
        if not editor.has_perm("accounts.change_customuser"):
            del self.fields["groups"]
        add_bootstrap_classes(self)


# from django.contrib.auth.forms import UserChangeForm

# class CustomUserChangeForm(UserChangeForm):
#     class Meta:
#         model = CustomUser
#         fields = ("email",)
