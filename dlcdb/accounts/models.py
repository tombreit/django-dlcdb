# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class CustomUserQuerySet(models.QuerySet):
    # Available only on QuerySet: delete() makes no sense on manager
    def delete(self):
        for obj in self:
            obj.is_active = False
            obj.save()

    delete.queryset_only = True


class CustomUserManager(UserManager):
    # TODO: makemigrations will refuse to do its work when 'use_in_migrations'
    # is set to True, which is the default value:
    # ValueError: Could not find manager CustomUserManagerFromCustomUserQuerySet in django.db.models.manager.
    # Please note that you need to inherit from managers you dynamically generated with 'from_queryset()'.
    #
    # Others have the same problem, eg:
    # https://github.com/raphaelm/django-scopes/issues/20
    use_in_migrations = False


class CustomUser(AbstractUser):
    # username_validator = UnicodeUsernameValidator()
    # username = models.CharField(
    #     _('username'),
    #     max_length=150,
    #     unique=True,
    #     help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
    #     validators=[username_validator],
    #     error_messages={
    #         'unique': _("A user with that username already exists."),
    #     },
    # )
    # USERNAME_FIELD = 'username'

    objects = CustomUserManager.from_queryset(CustomUserQuerySet)()

    def __str__(self):
        return self.username

    def delete(self):
        self.is_active = False
        self.save()
