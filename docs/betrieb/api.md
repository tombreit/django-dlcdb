# API

## Endpoints

*All endpoints are readonly.*

```{list-table}
   :widths: 20 50 30
   :header-rows: 1

   * - Case
     - Endpoint
     - Note
   * - Root
     - {{ api_base_url }}
     -
   * - Devices
     - {{ api_devices_url }}
     -
   * - Device by ``pk``
     - {{ api_device_by_pk_url }}
     -
   * - Filter Devices by EDV-ID
     - {{ api_device_by_id_url }}
     - *Note: Filter string must be an exact match.*
   * - Search Devices
     - {{ api_device_search_url }}
     -
   * - Persons with devices lent
     - {{ api_persons_with_devices }}
     - Filterable via ``?first_name=&last_name=&email=``
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
