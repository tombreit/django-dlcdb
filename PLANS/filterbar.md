<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Filterbar: tenant filter, backend cleanup, visible reset

**Status:** planned (2026-10-09). The overall design of the search and filter bar is the next
iteration (see *Open follow-ups*).

## Context

- Users can see several tenants (`request.tenants`, a tuple of `Tenant` set by
  `tenants/middleware.py`). The device list shows a Tenant column and sort only when
  `request.tenants|length > 1`, but nobody can narrow a list by tenant. The device admin already
  adds a tenant list filter under the same condition (`core/admin/device_admin.py:205`).
- The bar's reset control, "Clear all" ("Alle zurücksetzen"), is a `small` link inside the muted
  status line (`theme/filterbar/chips.html:25`), so it is easy to miss.
- Review of the filterbar backend: `theme/filterbar.py` is in good shape. The duplication is in
  the consumers:
  - nine views repeat "copy GET, setdefault ordering, bind the FilterSet", a convention the module
    docstring calls load-bearing;
  - `assets/filters.py` and `rooms/filters.py` carry five copies of a "true"/"false" method and
    three copies of the has-note filter.

  There is no measurable performance issue: each list runs the filtered COUNT once (paginator)
  plus one unfiltered COUNT.

## Decisions taken

1. **Tenant filter on every tenant-owned list:**
   - devices (`tenant`) and import history (`tenant`);
   - record trail, lendings and licences (`device__tenant`).

   Not on persons, rooms or device types, which no tenant owns.
2. **Single select** (`ModelChoiceFilter`, radio), like the admin's `RelatedOnlyFieldListFilter`,
   `inventory/filters.py:76` and every other device filter. It is the last primary filter on
   each list. Its empty label is `_("Any tenant...")`.
3. **Choices are the request's tenants, and only when there are two or more.** A new
   `filterable_tenants(request)` in `tenants/shortcuts.py` returns `Tenant.objects.none()`
   otherwise. The tenant scoping already narrows to a single tenant, so a filter would offer
   nothing.
4. **The filterbar skips a filter with nothing to choose** (no choice besides the empty reset).
   This one generic rule hides the tenant filter for single-tenant users. It also hides, for
   example, the "Import file" dropdown for a tenant without imports. FilterSets stay declarative:
   no `__init__` overrides.
5. **Reusable filter methods live in `dlcdb/theme/filters.py`** as plain functions for
   django-filter's `method=`, which accepts a callable:
   - `filter_boolean_choice(queryset, name, value)` for "true"/"false";
   - `filter_has_note(queryset, name, value)`, plus `HAS_NOTE_CHOICES`.

   No base class or mixin. Dead `if value else queryset` guards go away, because django-filter's
   `FilterMethod` never calls a method with an empty value.
6. **`bind_filterset(filterset_class, request, queryset, *, default_ordering)`** in
   `theme/filterbar.py` replaces the three-line binding block in every view. The load-bearing
   default ordering becomes code in one place instead of a convention in nine.
7. **The reset control is a button labelled "Clear filters":**
   - `btn btn-sm btn-outline-secondary` with a `bi-x-circle` icon, at the end of the chip row and
     in every empty state;
   - the label reuses the existing msgid "Clear filters" ("Filter zurücksetzen").

   This follows the Visa, Queensland Health and MoJ "filter a list" patterns: a real tertiary
   button after the removable tags, visible only while something is active. `_clear_all.html`
   loses its `label`/`link_class` parameters, and with them the label-leak caveat in
   `_list_status.html`. No SCSS or JS change: it stays an `<a data-filterbar-clear-all>` with its
   href fallback.

## Batches

### 1 — Tenant filter
- `tenants/shortcuts.py`: add `filterable_tenants(request)`:
  - `none()` without a request or with fewer than two tenants;
  - otherwise `Tenant.objects.filter(pk__in=[t.pk for t in request.tenants])`, ordered by
    `Tenant.Meta.ordering`.
- `theme/filterbar.py:_filter_spec`: return `None` when no choice has a non-empty value. Document
  this in the module docstring.
- Declare the filter and add it to `Meta.fields` after the last primary filter:
  - `assets/filters.py`: `DeviceFilter.tenant` and `RecordFilter.device__tenant`;
  - `lending/filters.py`: `LentRecordFilter.device__tenant`;
  - `licenses/filters.py`: `LicenceRecordFilter.device__tenant`;
  - `dataexchange/filters.py`: `ImporterListFilter.tenant`.
- CSV exports (devices, lendings) follow automatically: they share the bound FilterSet.
- Tests:
  - `tenants/tests/test_multi_tenant.py` (`MultiTenantUserTests`, tenants A + B + foreign):
    - the bar offers A and B, not the foreign tenant, on all five lists (add the view
      permissions the records and imports lists need);
    - `?tenant=<A>` narrows the device list;
    - `?tenant=<foreign>` is ignored without error.
  - `assets/tests/test_devices.py`: a single-tenant viewer (`_tenant_viewer`) gets no tenant
    filter.
  - `theme/tests/test_filterbar.py`: a ModelChoiceFilter over an empty queryset yields no spec.
- `NEWS.md`, one line: "Users who see several tenants can filter the device, record, lending,
  licence and import lists by tenant".
- Commit: `Filterbar, step 1: users with several tenants can filter the device, record, lending,
  licence and import lists by tenant`

### 2 — Backend cleanup (no behaviour change)
- New `theme/filters.py` (decision 5). Use it in:
  - `assets/filters.py`:
    - `is_lentable`, `is_imported` and `RecordFilter.is_active` use `filter_boolean_choice`;
    - both has-note filters use `filter_has_note`;
    - drop `lentable_filter`, `imported_filter`, `active_filter` and both `note_filter`s;
    - drop the dead `if value:` branch in `state_filter`. Keep the value check in
      `duplicate_filter`: it guards the `**{f"{value}__…"}` kwargs.
  - `rooms/filters.py`: drop `boolean_choice_filter` and `note_filter`.
- `theme/filterbar.py`:
  - add `bind_filterset` and update the docstring convention bullet;
  - read selected filter values from `request.GET.getlist(param)` like the sort already does.
    This drops `_raw_values` and gives one rule: "the bar reads what the user picked from the
    request";
  - drop the dead `isinstance(current, str)` branch in `_sort_options`;
  - share the "path + encoded query" tail of the two href helpers.
- Use `bind_filterset` in all nine call sites:
  - `assets/views/` `devices.py`, `records.py` and `masterdata.py`;
  - `rooms/views.py`, `persons/views.py`, `journal/views.py`, `dataexchange/views.py`;
  - `lending/views.py` (inside `_lending_filter`) and `licenses/views.py`.

  Each view reads `current_ordering` from `<filter>.data["ordering"]`.
- Tests: `test_filterbar.py` builds its view-shaped FilterSet via `bind_filterset`, and gets one
  test that an explicit `?ordering=` wins over the default. No NEWS.
- Commit: `Filterbar, step 2: shared true/false and has-note filter methods in theme/filters.py,
  bind_filterset() replaces the per-view default-ordering boilerplate`

### 3 — "Clear filters" button
- `theme/filterbar/_clear_all.html`:
  - always `btn btn-sm btn-outline-secondary text-nowrap` with a `bi bi-x-circle` icon and
    `{% translate "Clear filters" %}`;
  - drop the `label` and `link_class` parameters;
  - keep the comment on why it has no `hx-get`.
- Drop the parameters at every include:
  - `chips.html`;
  - the ten empty-state rows (journal, persons, licences, device types, suppliers, manufacturers,
    devices, records, rooms, importer index).
- Remove the label-leak paragraph from `theme/includes/_list_status.html`.
- `lending/index.html`: the empty state ("No devices found.") gets the include too.
- `assets/views/records.py:60`: docstring "Clear all" → "Clear filters".
- Tests:
  - `lending/tests/test_views.py` and `licenses/tests/test_views.py` assert on
    `data-filterbar-clear-all` instead of the label text;
  - delete `test_list_status_does_not_relabel_the_clear_all_link` in
    `theme/tests/test_shared_partials.py`, whose hazard no longer exists.
- No NEWS (UI polish).
- Commit: `Filterbar, step 3: the reset control is a "Clear filters" button next to the chips and
  in every empty state`

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| `__init__` in each FilterSet that deletes the tenant filter for single-tenant users | Five copies of the same override; the empty-choices rule is generic and correct on its own. |
| Hide filters with a *single* choice | Wrong in general: one room still narrows (devices without a room drop out). |
| Multi-select tenant filter | Admin, inventory and all device filters are single-select; "A and B" is rare and equals no filter for a two-tenant user. |
| Tenant filter as a FilterSet mixin / base class | No mixins (project convention); one declarative line per FilterSet is clearer. |
| `current_ordering` folded into `FilterBar` | Two similar notions on one object (the sort the user picked vs. the ordering in force). |
| Custom SCSS for the reset button | Bootstrap's `btn-sm btn-outline-secondary` is enough. |
| Reset control inside the bar row | The bar is not re-rendered by htmx (it keeps focus), so its visibility would need JS; this belongs to the bar redesign. |

## Open follow-ups

- **Bar redesign (next iteration):** planned in `PLANS/filterbar-redesign.md`. It covers:
  - layout of search, dropdowns and sort;
  - a reset inside the bar and the mobile offcanvas panel;
  - the status line, which is written three ways: `theme/includes/_list_status.html`,
    `lending/index.html:23` and `dataexchange/importer_index.html:23`.
- **Tenant column and sort** exist only on the device list. The record, lending, licence and
  import lists have none.
- **The device sort dropdown offers "Tenant" to single-tenant users**, while the column is hidden.
- **Lending runs a second COUNT:** the paginator counts on top of the state aggregate
  (`lending/views.py:138`).

## Pitfalls

- **Tenant choices must come from `request.tenants`**, never `Tenant.objects.all()`, which would
  show foreign tenant names.
- **Field paths differ:** `tenant` on devices and imports, `device__tenant` on records, lendings
  and licences.
- **The filter only narrows.** Visibility stays the job of `tenant_scoped_queryset`. A foreign id
  fails form validation and is dropped from `cleaned_data`.
- **A filter whose queryset is empty disappears from the bar.** That is by design (decision 4),
  so a "missing" dropdown on a fresh install is not a bug.

## Progress

- [x] 0 — This document
- [x] 1 — Tenant filter
- [x] 2 — Backend cleanup
- [ ] 3 — "Clear filters" button

## Verification (each batch)

- `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- `.venv/bin/pytest dlcdb/theme dlcdb/tenants dlcdb/assets dlcdb/rooms dlcdb/lending dlcdb/licenses dlcdb/dataexchange dlcdb/persons dlcdb/journal`, then `.venv/bin/pytest .`
- `/verify` skill (scratch DB, headless browser):
  - batch 1: a two-tenant user sees a "Tenant" dropdown on the five lists; picking A narrows the
    list and shows a "Tenant: A" chip; a single-tenant user sees no dropdown;
  - batch 3: screenshot the status line with chips + button and an empty state, desktop and
    mobile width; the button resets search, filters and sort in one request.
