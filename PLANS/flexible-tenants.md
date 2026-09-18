<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Flexible tenants: users in several tenants, plus an "all tenants" level

**Status:** design document, not implemented. Living document: update it when decisions or the
code change. Last revised 2026-09-18.

The behaviour this document wants to change is described (as it is today) in
`docs/guides/berechtigungen.md`, section *Tenants*.

## Problem

Each device is assigned to a tenant (`Device.tenant`). A user's tenant is derived from their
group memberships (`Tenant.groups`). Exactly one matching tenant is required: zero or several
matches yield "no tenant", an error banner on every request, and empty tenant-scoped lists.

The only way to see devices of more than one tenant is `is_superuser`, which also grants every
permission. There is no intermediate level. Example, a research institution:

- several research groups manage "their" devices autonomously (one tenant each);
- administrative units (IT, purchasing, finance, audit) must see or manage devices of several,
  possibly specific, tenants without being superusers.

## Decisions taken (2026-09-18)

1. **Permissions are identical in every tenant a user can access.** Tenants grant no
   permissions. Groups decide *what* a user may do, tenants decide *which devices* they see.
   No per-tenant roles.
2. **"All tenants" is a Django permission** `tenants.access_all_tenants` ("Can access devices of
   all tenants") on the `Tenant` model, assigned to groups. Superusers hold it implicitly via
   `user.has_perm`. Superuser keeps its meaning "all rights"; the permission only widens
   visibility.
3. **Write target** (new device, import, "save as new"): a `tenant` form field limited to the
   user's tenants. One tenant: preselected, effectively locked. Several: the user must choose.
   No session-level "active tenant" switcher.
4. **Multi-tenant users may move a device between the tenants they can access** (today:
   superuser only).

## Alternatives considered and rejected

| Approach | Example | Why not |
|---|---|---|
| Schema per tenant | django-tenants | Hard isolation at DB level; cross-tenant views (IT sees A and B) become impossible. |
| Explicit membership model with roles | django-organizations | Duplicates what groups already provide; LDAP mirror groups are the membership source here. |
| Object-level permissions | django-guardian, django-rules | Only needed for per-tenant roles, which decision 1 rules out. Touches every permission check. |
| Session "current tenant" plus allowed tenants | Odoo multi-company | Union semantics match, but a switcher adds UI state; decision 3 chose the form field instead. |
| Enforced default scoping (querysets refuse to evaluate without a scope) | django-scopes (pretix) | Good hardening, but a larger change; noted as follow-up. Today scoping is opt-in per view. |

## Current state (facts, after the independent fixes of September 2026)

- Membership: `Tenant.groups` (M2M to `auth.Group`). No `User.tenant` field. A user's tenant is
  computed per request by `dlcdb/tenants/shortcuts.py:get_current_tenant` and set as
  `request.tenant` by `dlcdb/tenants/middleware.py`. `request.tenant is None` means three
  things: superuser, no matching tenant, or several matching tenants.
- Read-side policy: `dlcdb/core/utils/tenants.py:tenant_scoped_queryset(queryset, request,
  tenant_field)`: tenant set → filter; else superuser → all; else nothing. Used by the assets,
  lending, dashboard, dataexchange apps and the `hints` context processor. The admin policy
  lives in `dlcdb/tenants/admin.py:TenantScopedAdmin` (used by `DeviceAdmin` and
  `LentRecordAdmin` only; the other record admins and `ImporterListAdmin` are unscoped).
- `InventoryQuerySet` (`dlcdb/core/models/inventory.py`) has its own `(tenant, is_superuser)`
  parameter style; `Inventory.device_search_tenant_aware = False` disables scoping for the
  inventory device search on purpose.
- Write side: forms (`dlcdb/assets/forms.py:DeviceForm`, `dlcdb/dataexchange/forms.py:DeviceImportForm`,
  `TenantScopedAdmin.get_form`) render the tenant field `disabled` for non-superusers and the
  views/admin overwrite `obj.tenant = request.tenant` on save
  (`dlcdb/assets/views/devices.py`, `dlcdb/dataexchange/views.py`, `TenantScopedAdmin.save_model`).
  The bulk relocate action (`dlcdb/core/forms/adminactions_forms.py`, `dlcdb/core/views/relocate_views.py`)
  allows a tenant change for superusers only.
- Only `core.Device` and `dataexchange.ImporterList` carry a tenant FK. Records, rooms, persons,
  notes, licences are scoped through `device__tenant`.
- The REST API (`dlcdb/api`) is unscoped by design and documented as such.
- Tenant column and badges are gated on `request.user.is_superuser` in templates
  (`dlcdb/assets/templates/assets/devices/index.html`, `dlcdb/theme/templates/theme/includes/navbar.html`,
  `dlcdb/tenants/templates/tenants/navbar_current_tenant.html`,
  `dlcdb/inventory/templates/inventory/partials/device_search_htmx.html`).

## Design

Keep `Tenant.groups` as the membership mechanism. Several matches become valid and mean the
**union** of those tenants. One small value object replaces the ambiguous `request.tenant`.

### `dlcdb/tenants/shortcuts.py` (rewrite, no `messages` side effects)

```python
@dataclass(frozen=True)
class TenantScope:
    tenants: tuple[Tenant, ...]   # via group membership; () when unrestricted
    unrestricted: bool            # user.has_perm("tenants.access_all_tenants"); True for superusers

    tenant_ids -> tuple[int, ...]
    single     -> the one tenant when len(tenants) == 1 and not unrestricted, else None
    multiple   -> unrestricted or len(tenants) > 1        # "show tenant column / selector"
    allows(tenant) -> unrestricted or (tenant is not None and tenant.pk in tenant_ids)
    q(tenant_field="tenant") -> Q() if unrestricted else Q(**{f"{tenant_field}__in": tenant_ids})
    tenant_queryset -> Tenant.objects.all() if unrestricted else Tenant.objects.filter(pk__in=tenant_ids)

ANONYMOUS_SCOPE = TenantScope((), False)
UNRESTRICTED_SCOPE = TenantScope((), True)

def get_tenant_scope(user) -> TenantScope:
    # not authenticated -> ANONYMOUS_SCOPE
    # user.has_perm("tenants.access_all_tenants") -> UNRESTRICTED_SCOPE
    # else tuple(Tenant.objects.filter(groups__in=user.groups.all()).distinct())

def scope_queryset(queryset, scope, *, tenant_field="tenant"):
    # queryset if scope.unrestricted else queryset.filter(scope.q(tenant_field))

def limit_tenant_field(field, scope):   # see "Forms"
```

`q()` exists so callers can put the tenant condition into the *same* `filter()` call as other
conditions on a multi-valued relation (rooms, persons via records). Scoping by ids is a plain
`WHERE tenant_id IN (...)`, no join, no `distinct` for devices. An empty `tenant_ids` yields an
empty result (`Count` annotations yield 0).

Why a value object: it replaces the `(tenant, is_superuser)` parameter pairs in
`InventoryQuerySet` and the three-way `None` in every consumer with one explicit type, built by
a pure function of the user.

### Middleware

`CurrentTenantMiddleware.process_request` sets `request.tenant_scope = get_tenant_scope(request.user)`.
`request.tenant` is **removed**, so stale consumers fail loudly instead of leaking. The
middleware position is unchanged (needs only `AuthenticationMiddleware`; the `MessageMiddleware`
dependency disappears with the messages).

### Permission and migration

`Tenant.Meta.permissions = [("access_all_tenants", "Can access devices of all tenants")]` plus
`dlcdb/tenants/migrations/0005_alter_tenant_options.py`. The `Permission` row is created by
`post_migrate`. Devices with `tenant = NULL` stay visible only to unrestricted users (unchanged:
`__in` never matches NULL).

### `dlcdb/core/utils/tenants.py`

Keep `tenant_scoped_queryset(queryset, request, *, tenant_field="tenant")` as the request-level
wrapper (signature unchanged, all call sites untouched). Body:
`scope_queryset(queryset, request.tenant_scope, tenant_field=tenant_field)` (plain attribute
access, no `getattr` fallback). Update the docstring: the admin now calls this, not vice versa.

### Forms: `limit_tenant_field(field, scope)`

One pure helper used by `DeviceForm`, `DeviceImportForm` and `TenantScopedAdmin.get_form`. It
drops the `disabled` trick and lets queryset validation do the work:

- unrestricted: `field.required = False` (unscoped devices remain possible, today's superuser
  behaviour); queryset all tenants.
- restricted: `field.queryset = scope.tenant_queryset`; field stays required (model
  `blank=False`). One tenant → `field.initial = scope.single`, `field.empty_label = None`: a
  one-option select, preselected; the POST carries the value; the queryset validates it.
  Several → the user must choose. Zero → empty select, form invalid, so a tenant-less user can
  no longer create devices that vanish into `tenant = NULL`.
- Verified against Django 6.1: a `ModelForm` built without an instance has an empty `initial`,
  so `field.initial` is honoured on add; with an instance the instance's tenant wins (edit
  form). The admin re-instantiates the form on POST with the posted value, so neither
  `disabled` nor `get_changeform_initial_data` is needed.

Views and admin stop overwriting `obj.tenant`; the limited queryset rejects foreign tenants.
`TenantScopedAdmin.save_model` keeps `scope.allows(obj.tenant)` as defence in depth
(`PermissionDenied`, only for models with a `tenant` field).

## Implementation steps

### 1. Tenants app core
- `dlcdb/tenants/models.py`: add `Meta.permissions`. Migration 0005.
- `dlcdb/tenants/shortcuts.py`: as designed above; delete `get_current_tenant`.
- `dlcdb/tenants/middleware.py`: set `request.tenant_scope`.
- `dlcdb/core/utils/tenants.py`: delegate to `scope_queryset`.
- `dlcdb/tenants/admin.py` `TenantScopedAdmin`: class attribute `tenant_lookup = "tenant"`;
  `get_queryset` → `tenant_scoped_queryset(super().get_queryset(request), request,
  tenant_field=self.tenant_lookup)` (one `super()` call; the MRO with
  `SoftDeleteModelAdmin.get_queryset` in `dlcdb/core/admin/base_admin.py` is fine, filtering
  chains on its ordered result). Remove `get_readonly_fields` (readonly excludes the field
  from the form and would block decision 4). `get_form`:
  `limit_tenant_field(form.base_fields["tenant"], request.tenant_scope)` when that field
  exists. `save_model`: the `allows` check. `TenantAdmin.list_display += ("group_names",)` so
  overlapping group assignments are visible.
- `dlcdb/core/admin/lentrecord_admin.py`: `tenant_lookup = "device__tenant"`.
- `dlcdb/core/admin/device_admin.py` `get_list_filter`/`get_list_display`: show the tenant
  column and filter when `request.tenant_scope.multiple`; use
  `("tenant", admin.RelatedOnlyFieldListFilter)`. Rename `get_superuser_list`
  (`dlcdb/core/utils/helpers.py`) to take a `show: bool`.

### 2. Frontend write paths
- `dlcdb/assets/forms.py` `DeviceForm.__init__`: replace the superuser branch with
  `limit_tenant_field(self.fields["tenant"], request.tenant_scope)`.
- `dlcdb/assets/views/devices.py` `device_add` / `device_detail`: delete the
  `device.tenant = request.tenant` overwrites ("save as new" posts to `device_add`, so it is
  covered).
- `dlcdb/dataexchange/forms.py` `DeviceImportForm.__init__`: same replacement.
  `dlcdb/dataexchange/views.py` `device_import`: delete the overwrite.
- `dlcdb/core/forms/adminactions_forms.py` `RelocateActionForm(*args, scope, **kwargs)` instead
  of `is_superuser`; `new_tenant.queryset = scope.tenant_queryset`; delete the `new_tenant`
  field when `not scope.multiple`; `clean_new_tenant` raises unless `scope.allows(new_tenant)`.
  `dlcdb/core/views/relocate_views.py`: pass `scope=self.request.tenant_scope` in
  `get_form_kwargs`. The template renders the form generically; nothing to do there.

### 3. Unify the read paths
- `dlcdb/dashboard/views.py` and `dlcdb/dashboard/stats.py`: already on
  `tenant_scoped_queryset`; only `distinct = ... and request.tenant is not None` becomes
  `... and not request.tenant_scope.unrestricted`, and the `Count(filter=...)` `Q` in
  `get_device_type_html` becomes `request.tenant_scope.q("device__tenant")`.
- `dlcdb/lending/filters.py` `current_borrowers`: `scope.q("record__device__tenant")` inside the
  single `filter()` call.
- `dlcdb/core/models/inventory.py` (`InventoryQuerySet`), keyword-only `scope`:
  `tenant_aware_device_objects(scope)`, `tenant_aware_device_objects_for_room(room_pk, scope)`,
  `inventory_relevant_devices(scope)` (unchanged `device_search_tenant_aware` semantics),
  `tenant_aware_room_objects(scope)` (one annotate branch:
  `Count(..., filter=Q(...) & scope.q("record__device__tenant"))`),
  `Inventory.get_inventory_progress(scope)`. Callers: `dlcdb/inventory/views.py`
  (`inventorize_room`, `InventorizeRoomListView`, `search_devices`, `QrCodesForRoomDetailView`,
  `get_note_btn`), `dlcdb/inventory/filters.py:RoomFilter`. In `search_devices`, narrow the
  `tenant` filter choices: `filter_devices.form.fields["tenant"].queryset = scope.tenant_queryset`.

### 4. Templates (no template tags; `request.tenant_scope` is reachable through the request context processor)
- Tenant column gating `is_superuser` → `request.tenant_scope.multiple`:
  `dlcdb/assets/templates/assets/devices/index.html`,
  `dlcdb/inventory/templates/inventory/partials/device_search_htmx.html`.
- Navbar badge (`dlcdb/theme/templates/theme/includes/navbar.html`,
  `dlcdb/tenants/templates/tenants/navbar_current_tenant.html`): three-way switch: unrestricted
  → "All tenants" (keep the red Superuser badge); tenants → `{{ scope.tenants|join:", " }}`;
  empty → warning "No tenant" (the admin navbar keeps its link to the tenant changelist).
- `dlcdb/inventory/templates/inventory/includes/inventory_progress.html`: "for your tenants".
- Afterwards `grep -rn 'request\.tenant\b\|request, "tenant"' dlcdb` must return nothing.

### 5. Optional, separate commit: scope the remaining admins
`RecordAdmin`, `OrderedRecordAdmin`, `InRoomRecordAdmin`, `LostRecordAdmin`, `RemovedRecordAdmin`,
`LicenceRecordAdmin` (`tenant_lookup = "device__tenant"`) and `ImporterListAdmin`
(`dlcdb/dataexchange/admin.py`, `"tenant"`) inherit `TenantScopedAdmin`. The record admins have
no `tenant` form field, so only `get_queryset` takes effect. At minimum do `ImporterListAdmin`,
so staff cannot import into arbitrary tenants from the admin. Behaviour change for staff users:
needs a line in `docs/guides/berechtigungen.md`.

### 6. Tests (`.venv/bin/pytest`)
Shared helper in `dlcdb/conftest.py`: `tenant_user(tenants=(), perms=(), all_tenants=False)`
building user, group(s) and `Tenant.groups` links; keep the `tenant` fixture. `RequestFactory`
tests must set `request.tenant_scope = get_tenant_scope(request.user)`. `has_perm` is cached per
user object; refetch after granting permissions.

- New `dlcdb/tenants/tests/test_scope.py`: `get_tenant_scope` for anonymous, zero, one (via two
  groups → still single), two tenants, `access_all_tenants` group member (unrestricted, not
  superuser), superuser; `allows`/`q`; `scope_queryset` hides NULL-tenant devices from
  restricted users and returns nothing for an empty scope; middleware sets `tenant_scope` and
  no `tenant`; `limit_tenant_field` for all four cases (queryset, required, initial, empty_label).
- `dlcdb/assets/tests/test_devices.py`: adapt the `RequestFactory` tests (single-tenant: one
  option, required, preselected; crafted foreign pk → form invalid). Add: add form saves the
  single tenant without a view overwrite; multi-tenant user must pick one of their tenants
  (missing → required, foreign → invalid choice, own second → saved); can move a device between
  own tenants on the detail page; sees the union in index/detail/CSV/search; tenant column shown
  for two-tenant and `access_all_tenants` users, hidden for single-tenant; zero-tenant user
  cannot create; `access_all_tenants` user sees NULL-tenant devices.
- `dlcdb/core/tests/test_device_admin.py`: changelist union and tenant column; add form offers
  only own tenants and rejects a foreign pk; single-tenant posts the only option; multi-tenant
  staff switches tenant on change; `access_all_tenants` staff sees everything.
- `dlcdb/dashboard/tests/test_tiles.py` and `test_search.py`: union and all-tenants cases.
- `dlcdb/inventory/tests/test_inventory.py`: replace `(tenant=None, is_superuser=True)` with
  `UNRESTRICTED_SCOPE`; room counts for a two-tenant union; `inventory_relevant_devices`
  respects the flag.
- `dlcdb/core/tests/test_relocate_views.py`: single-tenant user has no `new_tenant` field;
  multi-tenant user moves within own tenants, cannot pick a foreign one; `access_all_tenants`
  may pick any.
- `dlcdb/dataexchange/tests/test_frontend_import.py`: spoofing test passes without the
  overwrite; multi-tenant importer must choose / cannot spoof. `test_importer_listing.py`: union.
- Navbar badge rendering: "All tenants" / tenant names / "No tenant".

### 7. Docs and NEWS
- `docs/guides/berechtigungen.md`, section *Tenants*: union semantics, tenant selector when
  several, `access_all_tenants` (assign to groups; superusers implicit), zero tenants → "No
  tenant" badge and no devices, tenant change between own tenants, which admin pages remain
  unscoped; the superuser rows in the same page.
- `docs/faq.md` ("No tenant?": no error banner any more; several tenants is valid),
  `docs/guides/devices.md` (tenant column), `docs/guides/umziehen.md` (tenant change),
  `docs/betrieb/model.md` (Tenant paragraph), `docs/guides/erste_schritte.md` and
  `docs/guides/inventur.md` (wording).
- `NEWS.md`, one line each: users may belong to several tenants (union, tenant selector); new
  permission `tenants.access_all_tenants`; tenant-less users can no longer create unscoped
  devices.

## Pitfalls

Existing instances:
- Groups attached to several tenants currently produce an error banner and empty lists; after
  the upgrade those users **silently see the union**. Operators should review `Tenant.groups`
  overlaps before upgrading (the new `group_names` column in the Tenant admin; or in
  `manage.py shell` list users whose matched tenant count is greater than 1). Say so in NEWS.
- Users with no tenant could previously create devices with `tenant = NULL` (invisible to
  them). Now blocked by validation. Existing NULL-tenant devices are unaffected and remain
  visible only to unrestricted users.
- The red "no tenant" messages disappear; the navbar badge is the only hint. Update the FAQ.
- The `access_all_tenants` permission exists only after `migrate`; nobody holds it until a staff
  user assigns it to a group. On LDAP mirror groups the permission sticks to the existing DB
  group row, so it survives logins.
- Templates or local customisations reading `request.tenant` break (intended, loud).
- Tenant names appear in the tenant list filters; they were already shown in the navbar and are
  not secrets. `RelatedOnlyFieldListFilter` and the inventory filter narrowing limit them anyway.

New instances and in general:
- Scoping stays opt-in per view. The API is deliberately unscoped and documented; the record
  admins are unscoped unless step 5 is done. A django-scopes-style enforced default is the
  natural hardening if more apps are added.
- Multi-valued joins (`record__device__tenant__in` on rooms, device types, persons) need
  `distinct()` / `Count(distinct=True)` exactly as before, and the tenant condition must live in
  the same `filter()` call as sibling conditions on the same relation.
- Inventories with `device_search_tenant_aware = False` bypass scoping by design; unchanged.
- Overdue-lending notifications group by device tenant and use `Tenant.contact_email`; unchanged.
- LDAP: group membership is rewritten at login by `AUTH_LDAP_MIRROR_GROUPS`; multi-tenant IT
  staff need their LDAP group attached to each tenant, or the `access_all_tenants` permission.

## Verification

- `.venv/bin/pytest dlcdb` green, including the new scope tests.
- `.venv/bin/python manage.py makemigrations --check` shows nothing pending after 0005.
- With the `verify` skill: create tenants A and B and groups `ops-a` (A), `ops-b` (B), `it` (A
  and B), `audit` (`access_all_tenants` only, not superuser). Log in as each and check: device
  index counts and tenant column, add form choices and preselection, "save as new" keeps the
  chosen tenant, crafted POST with a foreign tenant rejected, detail page tenant switch for
  `it`, relocate action tenant choices, dashboard tiles and stats, inventory room counts and
  device search, CSV export, admin changelist/add/change, importer form, navbar badges.
- `grep -rn 'request\.tenant\b\|request, "tenant"' dlcdb` returns nothing.
