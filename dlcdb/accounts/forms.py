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

from .group_profiles import BY_KEY, GROUP_PROFILES
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
    A group's name, its permissions among DLCDB's own and its active members.
    What the form doesn't show stays as it is: the permissions no page of DLCDB
    checks, and deactivated members.

    ``own`` is ``permissions.own_permissions()``, ``editor`` the user saving.
    Members need ``accounts.view_customuser`` to be shown and
    ``accounts.change_customuser`` to be changed. LDAP sets a mirrored group's
    members and matches it by name: both are read-only.
    """

    permissions = forms.ModelMultipleChoiceField(queryset=Permission.objects.none(), required=False)
    members = _members_field()

    class Meta:
        model = Group
        fields = ["name"]

    def __init__(self, *args, own, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.own, self.editor = own, editor
        ldap = is_ldap_mirrored(self.instance)

        self.fields["permissions"].queryset = Permission.objects.filter(pk__in=[p.permission.pk for p in own])
        self.initial["permissions"] = list(self.instance.permissions.filter(pk__in=self.fields["permissions"].queryset))
        if ldap:
            self.fields["name"].disabled = True
            self.fields["name"].help_text = _("LDAP finds this group by its name, so it keeps it.")

        if not editor.has_perm("accounts.view_customuser"):
            del self.fields["members"]
        else:
            self.initial["members"] = list(self.instance.user_set.filter(is_active=True))
            self.fields["members"].disabled = ldap or not editor.has_perm("accounts.change_customuser")
        add_bootstrap_classes(self)

    def clean(self):
        cleaned_data = super().clean()
        permissions = set(cleaned_data.get("permissions", ()))
        # Add, change and delete need the model's view permission: granted along with them.
        permissions |= {p.requires for p in self.own if p.requires and p.permission in permissions}
        cleaned_data["permissions"] = permissions

        if not self._editor_keeps_change_group(permissions, cleaned_data.get("members")):
            raise ValidationError(
                _(
                    "You would lose the permission to change groups. Keep it in this group, or get it "
                    "through another group first."
                )
            )
        return cleaned_data

    def checked_permissions(self):
        """The permissions ticked on the page: as just submitted, or as saved."""
        if self.is_bound:
            return getattr(self, "cleaned_data", {}).get("permissions", set())
        return set(self.initial["permissions"])

    def save(self):
        group = super().save()
        others = list(group.permissions.exclude(pk__in=self.fields["permissions"].queryset))
        group.permissions.set([*others, *self.cleaned_data["permissions"]])
        if "members" in self.fields and not self.fields["members"].disabled:
            deactivated = list(group.user_set.filter(is_active=False))
            group.user_set.set([*deactivated, *self.cleaned_data["members"]])
        return group

    def _editor_keeps_change_group(self, permissions, members):
        """After the save, the editor may still change groups: through this group, or another way."""
        stays = self.editor in members if members is not None else self.instance.user_set.contains(self.editor)
        return (stays and _change_group() in permissions) or may_still_change_groups(self.editor, without=self.instance)


class NewGroupForm(forms.ModelForm):
    """
    A new group: its name, a group profile to start from, a tenant and members.
    The tenant needs ``tenants.change_tenant``, the members
    ``accounts.view_customuser`` and ``accounts.change_customuser``.
    """

    profile = forms.ChoiceField(
        label=_("Group profile"),
        choices=[("", _("None")), *((profile.key, profile.label) for profile in GROUP_PROFILES)],
        required=False,
        widget=forms.RadioSelect,
    )
    tenant = forms.ModelChoiceField(
        label=_("Tenant"),
        queryset=Tenant.objects.order_by("name"),
        required=False,
        help_text=_("Members see this tenant's devices. More tenants can be ticked on the group's page."),
    )
    members = _members_field()

    class Meta:
        model = Group
        fields = ["name"]

    def __init__(self, *args, editor, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        if getattr(settings, "AUTH_LDAP_MIRROR_GROUPS", None):
            self.fields["name"].help_text = _(
                "For an LDAP group, its exact name: LDAP then sets its members at their next login."
            )
        if not editor.has_perm("tenants.change_tenant"):
            del self.fields["tenant"]
        elif not self.fields["tenant"].queryset.exists():
            self.fields["tenant"].help_text = _("There are no tenants yet: add one under Settings › Tenants.")
        if not (editor.has_perm("accounts.view_customuser") and editor.has_perm("accounts.change_customuser")):
            del self.fields["members"]
        add_bootstrap_classes(self)

    def save(self):
        group = super().save()
        if profile := BY_KEY.get(self.cleaned_data["profile"]):
            group.permissions.add(*profile.permissions())
        if tenant := self.cleaned_data.get("tenant"):
            # Saved like a tick in the tenant matrix: stamped, into the tenant's history.
            tenant.groups.add(group)
            tenant.stamp_user(self.editor)
            tenant.save()
        if "members" in self.fields:
            group.user_set.set(self.cleaned_data["members"])
        return group


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
