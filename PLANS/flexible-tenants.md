<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Flexible tenants: open follow-ups

**Status:** implemented on branch `flexible-tenants` (2026-10-02): users in several tenants,
visibility only through groups, tenant management under *Settings › Tenants*. This document keeps
the decisions and what is still open. The implementation history is in git; the user-facing rules
are in `docs/guides/berechtigungen.md`, section *Tenants*.

## Decisions taken

1. **Permissions are identical in every tenant a user can access.** Tenants grant no permissions:
   groups decide *what* a user may do, tenants decide *which devices* they see. No per-tenant
   roles.
2. **Visibility comes only from `Tenant.groups`.** Several matching tenants mean their union.
   "All tenants" means attaching a group to every tenant, including each new one. No "all tenants"
   permission, no unfiltered bypass, no superuser exception. Escape hatch: a permission can be
   added later as one line in `get_user_tenants` (`Tenant.objects.all()` for its holders).
3. **Write target:** a `tenant` form field limited to the user's tenants
   (`tenants/shortcuts.py:limit_tenant_field`). One tenant: preselected. Several: the user
   chooses. No session-level "active tenant" switcher.
4. **Multi-tenant users may move a device between the tenants they can access.**
5. **A tenant is required on every create, edit and import, for everyone.**
6. **Licences are tenant-scoped like devices.**
7. **Devices and imports without tenant are cleaned up by hand:**
   - a sticky hint for the users who may assign them;
   - the Tenant admin action "Assign devices and imports without tenant";
   - no data migration, except imports whose devices share one tenant
     (`dataexchange/0008`);
   - both FKs are `on_delete=PROTECT`, so deleting a tenant creates no new orphans.
8. **Tenants are managed in the frontend** (group × tenant matrix, htmx, one save per click).
   Users, groups and permissions stay in the admin or LDAP. The tenant history (simple-history)
   is viewed in the admin.

## Alternatives considered and rejected

| Approach | Example | Why not |
|---|---|---|
| Schema per tenant | django-tenants | Hard isolation at DB level; cross-tenant views (IT sees A and B) become impossible. |
| Explicit membership model with roles | django-organizations | Duplicates what groups already provide; LDAP mirror groups are the membership source here. |
| Object-level permissions | django-guardian, django-rules | Only needed for per-tenant roles, which decision 1 rules out. Touches every permission check. |
| Session "current tenant" plus allowed tenants | Odoo multi-company | Union semantics match, but a switcher adds UI state; decision 3 chose the form field instead. |
| "Super tenant" flag on `Tenant` | former `Tenant.is_super_tenant` (removed in migration 0002) | Mixes membership with rights. |
| Permission `tenants.access_all_tenants` with an unfiltered bypass | earlier revision of this plan | Needs a second code path in every consumer and a second place to answer "who sees tenant X". Can be added later without the bypass (decision 2). |
| Soft delete for tenants | `SoftDeleteModelAdmin` | An UPDATE bypasses `PROTECT`; a "deleted" tenant would hide its devices without any hint. A hard delete of an empty tenant plus the history covers the audit need. |
| Per-tenant pages with a dual-pane widget | [filtered-select-multiple-widget](https://github.com/tombreit/filtered-select-multiple-widget) | Needs JS and a new dependency, and answers "who sees what" only one tenant at a time. The fallback if an instance outgrows the matrix (about 15 tenants, a few dozen groups). |

## Open follow-ups

### `Device.tenant` and `ImporterList.tenant` NOT NULL (next release)

Once production shows no "devices/imports without tenant" hint:
- add the migrations;
- give the tenant-less test device creations a tenant;
- remove in one go:
  - both hints (`core/context_processors.py:hints`);
  - the Tenant admin action and its page (`tenants/admin.py`, `tenants/actions/assign.html`);
  - their docs (`berechtigungen.md`, *Geräte und Importe ohne Tenant*).

Not on the branch, because the migration would fail on instances that still have orphans.

### Creator in `AuditBaseModel`

*Created* in the audit card (`theme/includes/_audit_data.html`) shows only a date: `user` is
"last changed by", so the creator is lost.
- **Fields:** `created_by` (FK, `SET_NULL`, `related_name="+"`) and `created_by_username` on
  `AuditBaseModel`.
- **Filling:** in `AuditBaseModel.save()`, when `self._state.adding`, copy `user`/`username`. Every
  create path already stamps `user` before saving.
- **Migrations:** one per app with audit models (core, dataexchange, smallstuff, tenants),
  including the history models of Device and Tenant.
- **Existing rows:** optional backfill from the `+` history entry where one exists.
- **Display:** *Created · user* like *Modified · user*.

### LDAP mirror groups before the first login

django-auth-ldap creates a mirrored group only when one of its members logs in. Until then it
cannot be attached to a tenant. Workaround today: create the group in the admin with the exact LDAP
name. Possible fix: create the `AUTH_LDAP_MIRROR_GROUPS` groups in `post_migrate`.

### Enforced scoping

Scoping is opt-in per view (`tenant_scoped_queryset`). A django-scopes-style default (querysets
refuse to evaluate without a scope) is the natural hardening if more apps are added.

### `DeviceAdmin.get_list_display` stores the request on the admin

`self.request = request` sets state on the shared `ModelAdmin` instance (thread-unsafe), so that a
display method can call `obj.get_state_data(user=self.request.user)`. This is older than the
tenant work.

## Pitfalls

- **Permissions carry over between tenants** (decision 1). A user in "ops-a" (edit, tenant A)
  and "audit-b" (view, tenant B) can edit B devices too. Use separate accounts where it matters.
  This is in `berechtigungen.md` and noted on the tenants page.
- **`tenants.change_tenant` decides visibility for everyone, the holder included:**
  - self-escalation: tick one's own group for any tenant;
  - withdrawal: untick a group and everyone in it loses access;
  - mail channel: a tenant's `contact_email` receives the overdue-lending mails for its devices,
    with borrower names.

  Recommendation in the docs: give it only to a group that is attached to every tenant anyway.
  Every change is in the tenant history.
- **New tenants are private until a group is ticked.** Forgetting fails closed: the group simply
  does not see the new tenant (a hole in an otherwise full matrix row).
- **Multi-valued joins** (`record__device__tenant__in` on rooms, device types, persons) need
  `distinct()` / `Count(distinct=True)`. The tenant condition must sit in the same `filter()` call
  as sibling conditions on the same relation.
- **Deliberately unscoped:**
  - the REST API;
  - inventory writes by uuid;
  - rooms frontend device counts;
  - notification reports;
  - the SAP comparison;
  - the admin's notes.

  `berechtigungen.md` lists the user-visible ones.
