# API

```{admonition} Interactive REST API Documentation
**{{ api_swagger_url }}**
```

## Token Authentication

API requests must be authenticated by a valid token.

Add a user with an unusable password and create a token for that user (`./manage.py shell`):

```python
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

# Add django user without password:
apiuser = get_user_model().objects.create_user("username")
apiuser.save()

# Generate token for that user:
Token.objects.create(user=apiuser)
```

The API user needs neither the staff nor the superuser flag. Note that the API
is **not** tenant-filtered: a token returns the devices of all tenants (see
[Berechtigungen › Mandanten](../guides/berechtigungen.md#mandanten)).

:::{note}
In your queries the token must be present via HTTP header, e.g.:

`Authorization: Token 9949899m0980f9418ad8464c345x4x4ee4b`
:::

## Endpoints

*All endpoints are readonly.* Base URL: {{ api_base_url }}

The reference below is generated automatically from the API source code at
build time, so it always matches the deployed API.

```{eval-rst}
.. openapi:: ../_generated/openapi.yaml
   :examples:
```
