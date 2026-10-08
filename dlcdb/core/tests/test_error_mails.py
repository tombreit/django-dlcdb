# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.contrib.auth import get_user_model
from django.core import mail


def test_test_error_url_mails_the_admins_a_traceback(client, settings, db):
    """/_500/ raises for a superuser: a 500, and the admins get the traceback by mail."""
    settings.ADMINS = ["admin@example.org"]
    superuser = get_user_model().objects.create_superuser(email="helpdesk@example.com", password="secret")
    client.force_login(superuser)
    client.raise_request_exception = False

    response = client.get("/_500/")

    assert response.status_code == 500
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["admin@example.org"]
    assert "RuntimeError" in mail.outbox[0].body


def test_test_error_url_is_for_superusers_only(client, settings, db):
    settings.ADMINS = ["admin@example.org"]

    response = client.get("/_500/")

    assert response.status_code == 302
    assert mail.outbox == []
