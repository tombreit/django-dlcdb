<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Field history: a frontend timeline of simple-history changes

**Status:** batch 1 done (2026-10-04): devices have the frontend field history; licences
follow in batch 2. This is a living document.

## Why

The field history of a device ("Felder Historie") is only the simple-history admin view, so only
staff see it. The licence history page is a separate, hand-rolled table. One read-only timeline
component in `dlcdb/theme/` should answer *when, who, what* for any model with
`HistoricalRecords()`.

## Decisions taken

1. **Pure helper + include**, like `paginate` and the filterbar: `dlcdb/theme/field_history.py:
   build_field_history(obj, *, exclude=(), secret=())` returns `HistoryEntry` dataclasses;
   `theme/includes/_field_history.html` renders them on the existing `.timeline`. No template
   tag, no new SCSS.
2. **One query.** `obj.history` (newest first by default) with `select_related("history_user",
   *tracked foreign keys)`; consecutive records are paired in Python and diffed with
   `diff_against(..., foreign_keys_are_objs=True)`. No `prev_record` (one query per row).
3. **What is shown:** a *Changed* entry with no visible change and no change reason is skipped;
   *Created* and *Deleted* are always shown. Fields come in model order, by verbose name. Empty
   values render as "—", choices by label, booleans as Yes/No, dates as `Y-m-d` like the rest
   of the frontend.
4. **Device:** `Device.FIELD_HISTORY_EXCLUDE = ("active_record", "user", "username",
   "deleted_by")`. The audit stamps repeat the history user, and state changes belong to the
   record trail. The encryption keys (`Device.FIELD_HISTORY_SECRET`) are **masked** for every
   viewer: "—" or "••••••", never the value.
5. **Permission:** the device page needs `core.view_device` and is tenant-scoped like the
   detail page (the admin's history also only needs the model's view permission). The licence
   page keeps `core.view_licencerecord`.
6. **Layout:** one timeline item per entry: date, user ("Unknown user" if none), action badge,
   change reason, then a `Field | Before | After` table. It is built from the Bootstrap grid, not
   `<table>`: the columns line up across entries, and on phones the field name takes its own line
   above Before | After. The newest item gets the filled "current" dot.

## Alternatives considered and rejected

- `simple_history.template_utils.HistoricalRecordContextHelper`: shortens values to 100 chars
  ("…[123 chars]…"; notes are the most-changed device field), prints `None` and `True` raw.
  It would need two of its four methods overridden, which is more code than a 10-line formatter.
- Showing `active_record`: its string is the record pk; 64 % of the device history rows change
  only `active_record` or the audit stamps (dev DB, 2026-10-04).
- A generic `/history/<content_type>/<pk>/` URL: each model has its own permission and tenant
  scoping, and a per-app view is ten lines.
- Pagination: at most 38 entries per device in the current data.

## Progress

- [x] Batch 0: this document
- [x] Batch 1: theme component, device field history page, sidebar link, docs
- [ ] Batch 2: licence history on the component, NEWS

## Open follow-ups

- Tenants (`m2m_fields=["groups"]`): m2m diff values are lists of through-row dicts. They need
  `simple_history.utils.get_m2m_reverse_field_name()` in the formatter before a Settings ›
  Tenants history page can use the component.
- Lending profiles and subscriptions: same component once their frontend pages want history.
- `DeviceAdmin.get_changed_fields` (admin) runs `prev_record` per row; it goes when the admin
  history is retired.

## Pitfalls

- With `foreign_keys_are_objs=True`, an *empty* foreign key comes back as
  `DeletedObject(pk=None)` ("Deleted manufacturer (pk=None)"), not `None`. The formatter shows "—".
- `diff_against` compares only *editable* tracked fields, so `created_at`, `modified_at`,
  `deleted_at` and `uuid` never appear.
- The `select_related` names come from `history.model.tracked_fields`, because a field excluded
  via `HistoricalRecords(excluded_fields=…)` does not exist on the historical model.
- Tests have no request, so they set `obj._history_user = user` before `save()`.
