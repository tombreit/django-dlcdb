# API

*All endpoints are readonly*

## API v2

```{list-table}
   :widths: 20 50 30
   :header-rows: 1

   * - Case
     - Endpoint
     - Note
   * - Root
     - https://fqdn/api/v2/
     -
   * - Devices
     - https://fqdn/api/v2/devices/
     -
   * - Device by ``pk``
     - https://fqdn/api/v2/devices/1689/
     -
   * - Filter Devices by EDV-ID
     - https://fqdn/api/v2/devices/?edv_id=NTB1146
     - *Hinweis: Filter-String muss exakt angegeben werden!*
   * - Search Devices
     - https://fqdn/api/v2/devices/?search=ntb1146
     -
   * - Persons with devices lent
     - https://fqdn/api/v2/persons/
     - filterable via ``?first_name=&last_name=&email=``
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
