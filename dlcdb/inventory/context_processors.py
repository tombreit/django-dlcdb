# SPDX-FileCopyrightText: 2026 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.conf import settings
from django.urls import reverse

from rest_framework.authtoken.models import Token

from dlcdb.core.models import Inventory


def _get_js_vars(request):
    """
    Expose some Django settings and other variables to the frontend.
    Will be consumed via:

    ```html
    {{ js_vars|json_script:"js_vars" }}
    ```

    ```javascript
    const jsVars = JSON.parse(document.getElementById('js_vars').textContent);
    const qrToggleUrl = jsVars.qrToggleUrl;
    ```
    """
    token = Token.objects.first()

    return {
        "qrCodePrefix": settings.QRCODE_PREFIX,
        "djangoDebug": settings.DEBUG,
        "apiBaseUrl": reverse("api-v2-root"),
        "apiToken": token.key if token else "",
        "qrToggleUrl": reverse("inventory:update-qrtoggle"),
        "qrScannerEnabled": bool(request.session.get("qrscanner_enabled")),
    }


def inventory(request):
    """
    Provide navbar context (active-inventory badge, QR toggle) and the js_vars
    JSON island on every inventory page.
    """
    resolver_match = getattr(request, "resolver_match", None)
    if not resolver_match or resolver_match.app_name != "inventory":
        return {}

    return {
        "current_inventory": Inventory.objects.active_inventory(),
        "js_vars": _get_js_vars(request),
    }
