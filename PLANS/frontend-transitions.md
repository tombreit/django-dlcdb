<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Every state change in the frontend

**Status:** in progress, batch 1 of 3 done: the assets device page runs Lose, Remove,
Restore and Recover in forms of its own. Before, they ran only in Django admin forms, which
need the Staff flag and an `add_*record` permission on top of the transition permission.
In the end every transition runs in the frontend, gated by `lifecycle.available` (its
transition permission) and the tenant scope alone, and the admin and frontend device pages
behave the same.

## Decisions taken

1. **Frontend flows on the assets device page** for `lose`, `remove`, `restore`,
   `recover`: one view `assets:device_transition` (`devices/<pk>/state/<name>/`), one
   small form per transition; it calls the `lifecycle.transition_*` function.
2. **The inventory device search routes to the same frontend flows** instead of the
   admin.
3. **Admin and frontend behave the same; no new code in the admins.** The admin is being
   phased out. Its forms may additionally need `is_staff` and their `add_*`/`change_*`
   permission. Aligning removes admin code, it never adds any.
4. **The same fields on both sides.** Remove: disposition state and whereabouts;
   attachments stay admin-only (managed there; the record detail page lists them). Lose
   and Restore: a note. Recover: room and note.
5. **Remove follows the lifecycle table everywhere**, including a device without any
   record (`None → REMOVED`), as the bulk remover does. The admin form's "localise it
   first" refusal is deleted: both device pages offered a button the form then refused.
6. **After a state change the user lands on the assets device page**, as after Order. The
   inventory example group holds `core.view_device`.
7. **Recover picks its room in a searchable select**, not the Move module: recovering
   stays a separate act with its own permission (`lifecycle.LOCALISING_MOVES`).

## Alternatives considered and rejected

- Drop the `is_staff` check in `_set_state.html` only: the admin would still refuse
  non-staff users.
- Let the admin add-forms check the transition permission: new admin code, for an admin
  that is being phased out.

## Open follow-ups

- An admin add-form opened directly (e.g. "Add" in a record list) checks only its
  `add_*record` permission, not the transition permission. Accepted until the admin forms
  are gone; via the device page the transition permission decides.

## Progress

- [x] 0. This document
- [x] 1. Lose, Remove, Restore, Recover on the assets device page; Remove aligned
- [ ] 2. The inventory device search uses the frontend flows
- [ ] 3. Docs (`berechtigungen.md`) and NEWS
