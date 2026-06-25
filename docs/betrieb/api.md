# API

```{admonition} Interactive REST API Documentation
**{{ api_swagger_url }}**
```

## Token Authentication

API requests must be authenticated by a valid token.

Add user with unusable password and get a token that user:

```bash
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

# Add django user without password:
apiuser = get_user_model().objects.create_user("username")
apiuser.save()

# Generate token for that user:
Token.objects.create(user=apiuser)
```

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
