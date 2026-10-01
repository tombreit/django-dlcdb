<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Flexible tenants: users in several tenants, visibility only through groups

**Status:** design document; steps 0–2 implemented (2026-10-01), step 3 open. Living
document: update it when decisions or the code change. Last revised 2026-10-01 (review against
the code on branch `flexible-tenants`; "all tenants" permission dropped in favour of plain
group attachment).

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
  possibly all, tenants without being superusers.

Goal beyond tenants: phase out `is_superuser` for everything that is not a Django admin feature.

## Decisions taken

1. **Permissions are identical in every tenant a user can access** (2026-09-18). Tenants grant
   no permissions. Groups decide *what* a user may do, tenants decide *which devices* they see.
   No per-tenant roles.
2. **Visibility comes only from `Tenant.groups`** (revised 2026-10-01). Several matching tenants
   mean their **union**. "All tenants" means attaching a group to every tenant, including each
   new one. No "all tenants" permission, no unfiltered bypass, no special case for superusers
   (after step 2). Escape hatch: a permission can be added later as one line in
   `get_user_tenants` (`Tenant.objects.all()` for its holders) plus a migration; no consumer
   changes.
3. **Write target** (new device, import, licence, "save as new"): a `tenant` form field limited
   to the user's tenants (2026-09-18). One tenant: preselected, the only option. Several: the
   user must choose. No session-level "active tenant" switcher.
4. **Multi-tenant users may move a device between the tenants they can access** (2026-09-18;
   today: superuser only).
5. **A tenant is required on every create, edit and import, for everyone** (2026-10-01). No new
   devices with `tenant = NULL`.
6. **Licences are tenant-scoped like devices** (2026-10-01): list, edit and history scoped;
   "new" gets the tenant field.
7. **Devices without a tenant are cleaned up by hand** (revised 2026-10-01). A sticky hint ("N
   devices without tenant!") points to a Tenant admin action with an intermediate page listing
   these devices; the user confirms the assignment there. No data migration. `Device.tenant`
   stays nullable but becomes `on_delete=PROTECT`, so deleting a tenant cannot create new
   orphans.

## Alternatives considered and rejected

| Approach | Example | Why not |
|---|---|---|
| Schema per tenant | django-tenants | Hard isolation at DB level; cross-tenant views (IT sees A and B) become impossible. |
| Explicit membership model with roles | django-organizations | Duplicates what groups already provide; LDAP mirror groups are the membership source here. |
| Object-level permissions | django-guardian, django-rules | Only needed for per-tenant roles, which decision 1 rules out. Touches every permission check. |
| Session "current tenant" plus allowed tenants | Odoo multi-company | Union semantics match, but a switcher adds UI state; decision 3 chose the form field instead. |
| "Super tenant" flag on `Tenant` | former `Tenant.is_super_tenant` (removed in migration 0002) | Mixes membership with rights. |
| Permission `tenants.access_all_tenants` with an unfiltered bypass | earlier revision of this plan | The bypass (`Q()` instead of `tenant__in`, to keep NULL-tenant devices visible) needs a second code path in every consumer, a value object, a migration, and a second place to answer "who sees tenant X". Can be added later without the bypass (see decision 2). |
| Enforced default scoping (querysets refuse to evaluate without a scope) | django-scopes (pretix) | Good hardening, but a larger change; noted as follow-up. Today scoping is opt-in per view. |

## Current state (verified 2026-10-01)

Membership and request attribute:
- `Tenant.groups` (M2M to `auth.Group`). A user's tenant is computed per request by
  `dlcdb/tenants/shortcuts.py:get_current_tenant` (with `messages` side effects) and set as
  `request.tenant` by `dlcdb/tenants/middleware.py`. `request.tenant is None` means three
  things: superuser, no matching tenant, or several matching tenants.

Read side:
- `dlcdb/core/utils/tenants.py:tenant_scoped_queryset(queryset, request, tenant_field)`: tenant
  set → filter; else superuser → all; else nothing. Used by assets (views, pickers, filters,
  records), lending (views, pickers), `dashboard/search.py`, dataexchange (importer list) and
  the `hints` context processor.
- **Not** on the helper, and **unscoped when `request.tenant is None`** (zero or several
  tenants, non-superuser):
  - `dlcdb/dashboard/views.py` (`_get_tenant_queryset`, overdue tile) and
    `dlcdb/dashboard/stats.py` (`tenant=None` → global counts and charts);
  - `dlcdb/lending/filters.py:current_borrowers` (all borrowers' names);
  - `InventoryQuerySet.tenant_aware_room_objects(tenant=None)` (global room counts).
- `InventoryQuerySet` (`dlcdb/core/models/inventory.py`) has its own `(tenant, is_superuser)`
  parameter style; `Inventory.device_search_tenant_aware = False` disables scoping for the
  inventory device search on purpose.
- The licences frontend (`dlcdb/licenses/views.py`) is tenant-unaware: `index` lists all
  `LicenceRecord`s, `edit` loads any `Device` by pk (not even restricted to `is_licence`),
  `history` any `LicenseAsset`, `new` saves licence devices with `tenant = NULL`.
- The admin policy lives in `dlcdb/tenants/admin.py:TenantScopedAdmin` (used by `DeviceAdmin`
  and `LentRecordAdmin` only; the other record admins and `ImporterListAdmin` are unscoped).

Write side:
- `dlcdb/assets/forms.py:DeviceForm`, `dlcdb/dataexchange/forms.py:DeviceImportForm` and
  `TenantScopedAdmin.get_form` render the tenant field `disabled` for non-superusers; views and
  admin overwrite `obj.tenant = request.tenant` on save (`assets/views/devices.py`,
  `dataexchange/views.py`, `TenantScopedAdmin.save_model`).
- Superusers may leave the tenant empty in the frontend forms, but the admin already requires
  it (model `blank=False`). Importing with `tenant=None` crashes on an existing device
  (`dataexchange/importer.py`, `tenant.pk`).
- Bulk relocate (`dlcdb/core/forms/adminactions_forms.py`, `dlcdb/core/views/relocate_views.py`):
  tenant change for superusers only, but `DevicesRelocateView.get_initial` loads
  `Device.objects.filter(pk__in=<?ids=>)` **unscoped**: anyone with the relocate permission can
  move any device by crafting the URL.
- `dataexchange/views.py:device_import_confirm` filters `tenant=getattr(request, "tenant", None)`,
  i.e. `tenant IS NULL` for a tenant-less user.
- `TenantAwareModel.tenant` (used by `Device`) was `on_delete=SET_NULL`: deleting a tenant
  orphaned its devices. Since step 0: `PROTECT` (migration `core/0077`).

Display:
- Tenant column and badges gated on `request.user.is_superuser` in
  `dlcdb/assets/templates/assets/devices/index.html`, `dlcdb/theme/templates/theme/includes/navbar.html`
  and `dlcdb/tenants/templates/tenants/navbar_current_tenant.html`. The inventory search
  (`inventory/partials/device_search_htmx.html`) always shows the column.
- `DeviceAdmin.get_list_filter`/`get_list_display` use `core/utils/helpers.py:get_superuser_list`,
  which mutates the class-level `list_filter`/`list_display` lists in place (state leaks across
  requests and threads).

Other:
- Only `core.Device` and `dataexchange.ImporterList` carry a tenant FK. Records, rooms, persons,
  notes, licences relate to a tenant through `device__tenant`.
- Dead code: `TenantManager.get_current` (calls a nonexistent method), the commented-out
  `TenantModelAdmin` in `tenants/admin.py`, `dashboard/stats.py:get_devices_by_series_data`.
- `core/tests/test_context_processor_queries.py` pins the `hints` processor to one room and one
  device query (two device queries since step 0, back to one in step 1).
- Verified on Django 6.1.1: an empty `__in` inside `Count(filter=...)` compiles to the constant
  `0`; `__in` never matches NULL.

Deliberately unscoped, unchanged by this plan (documented in `berechtigungen.md`):
- the REST API (`dlcdb/api`, read-only);
- inventory writes by uuid (`Inventory.inventorize_uuids_for_room`, `inventory/views.py:update_note_view`),
  consistent with `device_search_tenant_aware = False`;
- rooms frontend device counts (`rooms/views.py:_room_queryset`); rooms are shared;
- notification reports (`notifications/reports.py`).

## Design

A user's scope is the tuple of tenants whose groups they belong to. Every consumer filters with
a plain `tenant__in`. All tenant policy lives in the `tenants` app.

### `dlcdb/tenants/shortcuts.py` (rewrite, no `messages` side effects)

```python
def get_user_tenants(user):
    """Tenants whose groups the user belongs to; several tenants mean their union."""
    if not user.is_authenticated:
        return ()
    return tuple(Tenant.objects.filter(groups__in=user.groups.all()).distinct())


def tenant_scoped_queryset(queryset, request, *, tenant_field="tenant"):
    return queryset.filter(**{f"{tenant_field}__in": request.tenants})


def limit_tenant_field(field, tenants):
    """Offer only the given tenants; with exactly one, preselect it as the only option."""
    field.queryset = Tenant.objects.filter(pk__in=[tenant.pk for tenant in tenants])
    if len(tenants) == 1:
        field.initial = tenants[0]
        field.empty_label = None
```

- Consumers use plain lookups: `tenant_scoped_queryset` for querysets,
  `Q(device__tenant__in=request.tenants)` inside `Count(filter=...)` and in the same `filter()`
  call as sibling conditions on multi-valued relations, `tenant in request.tenants` for single
  objects, `request.tenants|length > 1` in templates.
- An empty tuple yields an empty result (`Count` annotations yield 0). Devices with
  `tenant = NULL` are visible to nobody in the frontend and admin lists; see *Devices without a
  tenant*.
- `limit_tenant_field`: the field stays required (model `blank=False`, decision 5). One tenant:
  one-option select, preselected, the POST carries the value. Several: the user must choose.
  Zero: empty select, form invalid. A `ModelForm` without instance honours `field.initial`; with
  an instance, the instance's tenant wins. Views and admin stop overwriting `obj.tenant`; the
  limited queryset rejects foreign tenants.

### Middleware

`CurrentTenantMiddleware.process_request` sets `request.tenants = get_user_tenants(request.user)`.
`request.tenant` is **removed**. Position unchanged (needs only `AuthenticationMiddleware`; the
`MessageMiddleware` dependency disappears with the messages).

Only Python attribute access `request.tenant` fails loudly. `getattr(request, "tenant", None)`
and template lookups fail silently, so the grep in *Verification* is a required gate.

### Admin: `TenantScopedAdmin`

- `tenant_lookup = "tenant"` class attribute; `get_queryset` →
  `tenant_scoped_queryset(super().get_queryset(request), request, tenant_field=self.tenant_lookup)`
  (chains on `SoftDeleteModelAdmin.get_queryset` in `dlcdb/core/admin/base_admin.py`).
- `formfield_for_foreignkey`: `limit_tenant_field(formfield, request.tenants)` for
  `db_field.name == "tenant"` (documented hook; replaces mutating `form.base_fields`).
- Delete `get_readonly_fields` (readonly would block decision 4), `get_form` and `save_model`.
- `TenantScopedRecordAdmin(TenantScopedAdmin)` with `tenant_lookup = "device__tenant"`: the
  parent of all record admins (records carry no tenant of their own).

### Display

- Tenant column (`assets/devices/index.html` incl. `colspan`, `inventory/partials/device_search_htmx.html`)
  and the `DeviceAdmin` tenant column and filter (`("tenant", admin.RelatedOnlyFieldListFilter)`,
  built as a new list, no class attribute mutation) only when `request.tenants|length > 1`.
- Navbar badge (`theme/includes/navbar.html`, `tenants/navbar_current_tenant.html`): one tenant →
  its name; several → "N tenants" with the names in the `title`; none → no badge. The red
  Superuser badge stays; from step 2 on without the title "Superusers are not tenant aware".
  Strings translatable.
- No tenant → sticky hint in `core/context_processors.py:hints` (only with `core.view_device`):
  "None of your groups belongs to a tenant, so you see no devices.", linking to the Tenant admin.
  Together with the "devices without tenant" hint it tells an operator what to configure after
  an update.

### Devices without a tenant: hint and Tenant admin action

**Hint** (`dlcdb/core/context_processors.py:hints`, same pattern as "N devices without
record!", shown to everyone like the room and branding hints):
- `StickyMessage(level=WARNING, msg=ngettext("%(count)d device without tenant!", ...),
  cta_link=reverse("admin:tenants_tenant_changelist"), cta_text=_("Assign a tenant?"))`.
- The count is global on purpose: these devices belong to no tenant. Same queryset as the
  admin view: `Device.objects.filter(tenant__isnull=True)`.
- From step 1 on, one aggregate serves both device hints, keeping the pinned query count:
  `Device.objects.aggregate(recordless=Count("pk", filter=Q(tenant__in=request.tenants, active_record__isnull=True)), single_recordless_pk=Min(..., same filter), without_tenant=Count("pk", filter=Q(tenant__isnull=True)))`.

**Tenant admin action with an intermediate page** (`dlcdb/tenants/admin.py:TenantAdmin`),
following the Django docs, *Actions that provide intermediate pages*: the action redirects to a
view we write (same pattern as `DeviceAdmin.relocate` → `core/views/relocate_views.py`).
- Action `assign_devices_without_tenant` ("Assign devices without tenant"): exactly one selected
  tenant → `HttpResponseRedirect(reverse("admin:tenants_tenant_assign_devices", args=[tenant.pk]))`;
  otherwise `message_user` "Please select exactly one tenant." (error).
- Permission: `permissions=["assign_devices"]` plus `has_assign_devices_permission(request)`
  checking `tenants.change_tenant` **and** `core.change_device` (several listed action
  permissions are OR-ed, hence one method).
- View: `TenantAdmin.get_urls()` adds `<int:tenant_id>/assign-devices/` wrapped in
  `self.admin_site.admin_view(...)` (same as the deactivate/activate views in
  `SoftDeleteModelAdmin.get_urls`).
- `assign_devices_view(request, tenant_id)`: same permission check, else `PermissionDenied`;
  `get_object_or_404(Tenant, pk=tenant_id)`; `devices = Device.objects.filter(tenant__isnull=True)`.
  - GET: `TemplateResponse` with `tenants/actions/assign_devices.html` (extends
    `admin/base_site.html` like `core/actions/relocate.html`; context includes
    `self.admin_site.each_context(request)` and `opts`): the target tenant, a table of all
    tenant-less devices (device, type, licence, room, record) with a **pre-checked checkbox**
    each, an "Assign to <tenant>" button and a "No, take me back" link to the tenant changelist;
    "No devices without tenant." when empty.
  - POST: `devices.filter(pk__in=request.POST.getlist("device"))`: only the confirmed devices
    that are still tenant-less; a crafted pk of a device with a tenant is ignored. In
    `transaction.atomic()`, save each device (not `.update()`) with
    `get_denormalized_user(request.user)`, so simple-history and the audit fields record it (as
    the relocate view does). `message_user` with the count, redirect to the tenant changelist.
  - Checkboxes: the user approves exactly the listed devices, and orphans belonging to
    different tenants can be assigned one tenant at a time.

## Implementation steps

### Step 0: stop new orphans, report old ones (implemented 2026-10-01)

- Hint and Tenant admin action as designed. In step 0 the hint's count is its own query (the
  recordless aggregate is still scoped by the old `tenant_scoped_queryset`);
  `test_context_processor_queries.py` is adjusted to two device queries and back to one in
  step 1.
- `dlcdb/tenants/models.py:TenantAwareModel.tenant` → `on_delete=models.PROTECT`; state-only
  `AlterField` migration in `core` (`on_delete` is not part of the schema).
- `DeviceForm` and `DeviceImportForm`: delete the superuser branch's `required = False`
  (decision 5).
- Operators assign the existing orphans (likely mostly licences, see *Current state*) with the
  action: one run per target tenant, unchecking devices that belong elsewhere. Any time, before or
  after the later steps (see the upgrade notes).

### Step 1: prep, tuple model with today's rules (implemented 2026-10-01)

Deviations from the list below, found during implementation:
- `inventory/partials/device_search_htmx.html` keeps its tenant column for everyone: with
  `device_search_tenant_aware = False` the search spans all tenants, so even single-tenant users
  need it.
- `dashboard/views.py:_get_tenant_queryset` stays (now taking `request`): it separates the
  tenant-aware tile models from the others.
- The grep gate below also matches the unrelated `createsuperuser` error message in
  `accounts/models.py`.
- Test fixtures: `BaseTest._create_device` and the conftest device fixtures now give devices a
  tenant (superusers no longer see devices without one); tests about orphans use
  `Device.objects.create()` directly.

`get_user_tenants` reproduces today's visibility with two marked lines, removed in step 2:

```python
    if user.is_superuser:  # step 1 only
        return tuple(Tenant.objects.all())
    tenants = tuple(Tenant.objects.filter(groups__in=user.groups.all()).distinct())
    return tenants if len(tenants) == 1 else ()  # step 1 only: several stay ambiguous
```

Tenants app (consolidation):
- `dlcdb/tenants/shortcuts.py`: as designed; delete `get_current_tenant`.
- Move `tenant_scoped_queryset` from `dlcdb/core/utils/tenants.py` into the tenants app and
  delete the core module; update the imports (assets views/pickers/filters/records, lending
  views/pickers, dashboard search, dataexchange views, `core/context_processors.py`).
- `dlcdb/tenants/middleware.py`: set `request.tenants`.
- `dlcdb/tenants/admin.py`: `TenantScopedAdmin` as designed; delete the commented
  `TenantModelAdmin` block; `TenantAdmin.list_display += ("group_names",)` (with
  `prefetch_related("groups")`) so operators can review overlaps before step 2.
- `dlcdb/tenants/models.py`: delete `TenantManager` (its `get_current` is broken).

Read paths:
- `dlcdb/dashboard/views.py`: `_build_tile` takes `request`; scoped models via
  `tenant_scoped_queryset(ModelClass.objects.all(), request, tenant_field=TENANT_FILTERS[model])`;
  `distinct = model_name in TENANT_DISTINCT`; overdue tile via the helper (`"device__tenant"`).
  Delete `_get_tenant_queryset`.
- `dlcdb/dashboard/stats.py`: the three chart functions take `tenants` and filter with
  `device__tenant__in=tenants` (`Count(filter=Q(...))` for device types); delete
  `get_devices_by_series_data`.
- `dlcdb/lending/filters.py:current_borrowers`: one `filter(record__record_type=..., record__is_active=True, record__device__tenant__in=request.tenants)`;
  no request → `Person.objects.none()`.
- `dlcdb/core/models/inventory.py` (`InventoryQuerySet`), keyword-only `tenants` instead of
  `(tenant, is_superuser)`: `tenant_aware_device_objects`, `tenant_aware_device_objects_for_room`,
  `inventory_relevant_devices` (unchanged `device_search_tenant_aware` semantics),
  `tenant_aware_room_objects` (one annotate branch with `record__device__tenant__in=tenants`
  inside the `Count` filters), `Inventory.get_inventory_progress`. Callers:
  `dlcdb/inventory/views.py` (`inventorize_room`, `InventorizeRoomListView`, `search_devices`,
  `QrCodesForRoomDetailView`, `get_note_btn`), `dlcdb/inventory/filters.py:RoomFilter`.
- `dlcdb/core/context_processors.py:hints`: one device aggregate (see *Hint*).

Holes:
- `dlcdb/core/views/relocate_views.py`: `get_initial` scopes the devices with
  `tenant_scoped_queryset`; `get_form_kwargs` passes `tenants=self.request.tenants`.
- `dlcdb/core/forms/adminactions_forms.py` `RelocateActionForm(*args, tenants, **kwargs)`:
  `limit_tenant_field(self.fields["new_tenant"], tenants)` when `len(tenants) > 1`, else delete
  the field; delete `clean_new_tenant` (queryset validation covers it).
- `dlcdb/dataexchange/views.py:device_import_confirm`: look up via `_importer_list_queryset(request)`.
- `dlcdb/licenses/views.py`: `index` via `tenant_scoped_queryset(..., tenant_field="device__tenant")`;
  `edit` via `tenant_scoped_queryset(Device.objects.filter(is_licence=True), request)`;
  `history` via `tenant_scoped_queryset(LicenseAsset.objects.all(), request)`.
  `dlcdb/licenses/forms.py:LicenseForm`: add `"tenant"` to `fields` and a `Column("tenant")` to
  the crispy layout; takes `tenants` and calls `limit_tenant_field`.

Write paths:
- `DeviceForm.__init__` and `DeviceImportForm.__init__`: replace the superuser branch with
  `limit_tenant_field(self.fields["tenant"], request.tenants)`.
- `dlcdb/assets/views/devices.py` (`device_add`, `device_detail`) and
  `dlcdb/dataexchange/views.py:device_import`: delete the `obj.tenant = ...` overwrites ("save as
  new" posts to `device_add`, so it is covered).

Display: as designed. `dlcdb/core/admin/lentrecord_admin.py`: scoped through the device
(now via `TenantScopedRecordAdmin`, see step 3).
Delete `core/utils/helpers.py:get_superuser_list`.
`dlcdb/inventory/templates/inventory/includes/inventory_progress.html`: "for your tenants".

Intended behaviour changes (docs + NEWS):
- Non-superusers with zero or several tenants see zeros on the dashboard instead of global
  numbers, and no foreign borrowers.
- Superusers no longer see devices without a tenant (the hint and the Tenant admin action
  remain).
- Tenant-less users can no longer create devices.
- Licences are tenant-scoped.
- No more red "no tenant"/"several tenants" message banners; the navbar badge is the hint.

### Step 2: the switch (implemented 2026-10-01)

Delete the two marked lines in `get_user_tenants`, ideally as two commits:
- 2a: several matching tenants mean their union;
- 2b: superusers see the tenants of their groups like everyone else.

Plus the Superuser badge title, docs, NEWS and the upgrade notes.

### Step 3: optional follow-ups (separate commits)

- *(done)* Scope the remaining admins: `ImporterListAdmin` (`dlcdb/dataexchange/admin.py`, at minimum, so
  staff cannot import into arbitrary tenants), `RecordAdmin`, `OrderedRecordAdmin`,
  `InRoomRecordAdmin`, `LostRecordAdmin`, `RemovedRecordAdmin`, `LicenceRecordAdmin`
  (via `TenantScopedRecordAdmin`; no tenant form field, so `get_queryset` and the device choices apply).
  Behaviour change for staff users: one line in `berechtigungen.md`. Also check if the related non-admin-views are also tenant-scoped (eg. `importer_index`).
  Done: `TenantScopedAdmin` also limits every device FK (forged pks fail) and
  `CustomBaseProxyModelAdmin.add_view` scopes `?device=`. The non-admin views were already scoped.
  `NoteAdmin` stays unscoped (decision 2026-10-01; room notes have no tenant), attachments too.
- *(done)* Inventory device search: narrow the `tenant` filter choices to `request.tenants`, but only
  when `device_search_tenant_aware` (otherwise the search spans all tenants).
- *(deferred to a later release)* `Device.tenant` NOT NULL: once production shows no "devices
  without tenant" message, add the migration, give the ~62 tenant-less test device creations a
  tenant, and remove the orphan message, the Tenant admin action and their docs in one go. Not
  on this branch: the migration would fail on instances that still have orphans.
- Phase out the remaining non-admin `is_superuser` checks: `DeviceForm.clean_is_lentable`,
  `theme/includes/navbar.html` (staff-or-superuser link), `core/context_processors.py:nav`
  (redundant `or is_superuser`, `has_perm` already covers it). Admin-only checks
  (`base_admin.py`, restore action) stay.

## Tests (`.venv/bin/pytest`)

Shared helper in `dlcdb/conftest.py`: `tenant_user(tenants=(), perms=())` building user,
group(s) and `Tenant.groups` links; keep the `tenant` fixture. `RequestFactory` tests set
`request.tenants = get_user_tenants(request.user)`. `has_perm` is cached per user object;
refetch after granting permissions.

Step 0:
- `dlcdb/core/tests/test_hints.py`: "devices without tenant" hint with the right count when
  NULL-tenant devices exist, absent otherwise.
- `dlcdb/tenants/tests/test_admin.py` (new): action with one tenant → redirect to the page; zero
  or several → error message; GET lists only tenant-less devices and the target tenant; POST
  assigns only checked, still tenant-less devices, records history and the audit user, ignores
  a crafted pk of a device with a tenant; without both permissions the action is hidden and the
  view returns 403.
- Deleting a tenant with devices raises `ProtectedError`.
- `DeviceForm`/`DeviceImportForm`: superuser must choose a tenant.

Step 1:
- `dlcdb/tenants/tests/test_shortcuts.py` (rewrite; the message tests go): `get_user_tenants`
  for anonymous, zero, one (via two groups → still one), two (→ empty, step 1 rule),
  superuser (→ all tenant rows); `tenant_scoped_queryset` hides NULL-tenant devices and
  returns nothing for an empty tuple; middleware sets `tenants` and no `tenant`;
  `limit_tenant_field` for zero, one, several (queryset, initial, empty_label).
- `dlcdb/assets/tests/test_devices.py`: single-tenant add form saves the only option without a
  view overwrite; crafted foreign pk → invalid; zero-tenant user cannot create.
- `dlcdb/core/tests/test_relocate_views.py`: crafted `?ids=` of a foreign device is ignored;
  `new_tenant` only with several tenants.
- `dlcdb/dataexchange/tests/test_frontend_import.py`: spoofing test passes without the
  overwrite; tenant-less user cannot confirm a NULL-tenant import.
- `dlcdb/dashboard/tests/test_tiles.py`: zero-tenant user sees 0 (was global).
- `dlcdb/licenses/tests/test_views.py`: list/edit/history scoped; edit 404 for a non-licence
  device; new requires a tenant.
- `dlcdb/core/tests/test_device_admin.py`: add form offers only own tenants and rejects a foreign
  pk; a request with several tenants does not leak the tenant column into a following
  single-tenant request.
- `dlcdb/inventory/tests/test_inventory.py`: replace `(tenant=None, is_superuser=True)` with
  `tenants=(...)`; `inventory_relevant_devices` respects the flag.
- `core/tests/test_context_processor_queries.py`: back to one device query.
- Navbar badge: tenant name / "N tenants"; no tenant → sticky hint (only with `core.view_device`).
- Tests that view tenant-less devices as a superuser give those devices the `tenant` fixture.

Step 2:
- Two tenants → union (flips the step 1 test); superuser without groups sees nothing.
- Multi-tenant user: sees the union in device index/detail/CSV/search, dashboard, lending,
  licences, importer listing, inventory room counts; tenant column shown; must pick one of their
  tenants on add (missing → required, foreign → invalid, own second → saved); moves a device
  between own tenants on the detail page, in the admin and via relocate, never into a foreign
  one.
- Superuser shortcut tests switch to `tenant_user(tenants=..., perms=...)` (matches the docs'
  rule "never test permissions as a superuser").

## Docs and NEWS

- `docs/guides/berechtigungen.md`: *Tenants* section (union semantics, tenant selector when
  several, "all tenants" = attach a group to every tenant and to each new one, zero tenants →
  sticky hint and no devices, tenant always required, tenant change between own tenants,
  licences scoped, devices without a tenant: the hint and the Tenant admin action, permissions
  apply in every accessible tenant (see *Pitfalls*), the deliberately unscoped areas); superuser
  rows: all permissions, but only the tenants of their groups.
- `docs/faq.md` (the "no tenant" hint and how to fix it),
  `docs/guides/devices.md` (tenant column, tenant field), `docs/guides/lizenzen.md` (tenant
  field), `docs/guides/umziehen.md` (tenant change), `docs/betrieb/model.md` (Tenant paragraph:
  PROTECT), `docs/guides/erste_schritte.md` (step 4: attach the admin group too) and
  `docs/guides/inventur.md` (wording).
- `NEWS.md`, one short line each. Step 0: hint and admin action for devices without tenant;
  tenants with devices can no longer be deleted; superusers must choose a tenant. Step 1:
  dashboard/lending scoping fix; relocate action scoped; licences tenant-scoped. Step 2: users
  may belong to several tenants (union); superusers see only their groups' tenants.

Upgrade notes: steps 0–2 deploy in one go, no prescribed order and no upgrade guide. What
needs configuring announces itself: the sticky hints for "no tenant" and "devices without
tenant" (both linking to the Tenant admin). NEWS has one entry.

## Pitfalls

- **Permissions carry over between tenants** (consequence of decision 1): a user in "ops-a"
  (edit permissions, tenant A) and "audit-b" (view permissions, tenant B) can edit B devices
  too. Per-tenant roles are not expressible; use separate accounts where it matters.
- **New tenants are private until groups are attached.** Attach the IT/audit groups in the
  Tenant add form. Forgetting fails closed: IT simply does not see the new tenant.
- Groups attached to several tenants currently produce empty lists; after step 2 those users
  **silently see the union**. See the upgrade notes.
- LDAP admins (superusers) lose their device overview in step 2 until their mirrored group is
  attached to the tenants.
- Devices without a tenant are listed only on the Tenant admin action's intermediate page (and
  reachable via shell and API).
- Deleting a tenant with devices is blocked (`PROTECT`); move its devices first.
- Templates and `getattr(request, "tenant", None)` fail silently after `request.tenant` is gone;
  the grep gate catches them, including local customisations.
- Fresh installs need a Tenant before the first device (decision 5); *Erste Schritte* step 4
  already creates one.
- Multi-valued joins (`record__device__tenant__in` on rooms, device types, persons) need
  `distinct()` / `Count(distinct=True)`, and the tenant condition must live in the same
  `filter()` call as sibling conditions on the same relation.
- Scoping stays opt-in per view. A django-scopes-style enforced default is the natural hardening
  if more apps are added.
- Overdue-lending notifications group by device tenant and use `Tenant.contact_email`; unchanged.

## Verification

- `.venv/bin/pytest dlcdb` green after each step.
- After step 0: `.venv/bin/python manage.py makemigrations --check` shows nothing pending.
- After step 1: `grep -rn --exclude-dir=tests 'request\.tenant\b\|request, "tenant"\|is_superuser=' dlcdb`
  returns nothing.
- With the `verify` skill:
  - step 0: create a device without tenant → the hint shows, its link leads to the Tenant
    changelist, the action's intermediate page lists the device and the selected tenant,
    confirming assigns it (history entry), the hint disappears; deleting a tenant with devices
    is refused.
  - step 1: users of tenants A and B and a superuser behave as on `main`, except for the
    intended behaviour changes listed in step 1.
  - step 2: tenants A and B, groups `ops-a` (A), `ops-b` (B), `it` and `audit` (both attached to
    A and B), a superuser without groups. Log in as each and check: device index counts and
    tenant column, add form choices and preselection, "save as new" keeps the chosen tenant,
    crafted POST with a foreign tenant rejected, detail page tenant switch for `it`, relocate
    action tenant choices and crafted `?ids=`, dashboard tiles and stats, lending borrower
    filter, licences, inventory room counts and device search, CSV export, admin
    changelist/add/change, importer form and confirm, navbar badges; the superuser sees nothing.
