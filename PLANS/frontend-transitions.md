<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Every state change in the frontend

**Status:** implemented (2026-10-14). Every transition runs in the frontend,
gated by `lifecycle.available` (its transition permission) and the tenant scope alone: the
assets device page runs Lose, Remove, Restore and Recover in forms of its own, the
inventory device search uses the same screens, returns to itself afterwards and has no
admin links left, and the admin's device page opens these screens too. Before, the four ran
only in Django admin forms, which need the Staff flag and an `add_*record` permission on top
of the transition permission. The admin code that only served the record add-forms is
gone.

## Decisions taken

1. **Frontend flows on the assets device page** for `lose`, `remove`, `restore`,
   `recover`: one view `assets:device_transition` (`devices/<pk>/state/<name>/`), one
   small form per transition; it calls the `lifecycle.transition_*` function.
2. **The inventory device search routes to the same frontend flows** instead of the
   admin.
3. **The admin uses the frontend screens; no new code in the admins.** The admin is being
   phased out. Its device page opens the same frontend screens (Order as a link to the
   device page: the admin's device list renders the buttons inside its own form), and the
   ordered, room-assignment, not-locatable and removed record admins offer no "Add", like
   the lending, licence and record admins already. Their add-forms checked only
   `add_*record`, not the transition permission, so `core.add_inroomrecord` could recover
   a decommissioned device. Aligning removes admin code, it never adds any.
4. **The same fields on both sides.** Remove: disposition state and whereabouts;
   attachments stay admin-only (managed there; the record detail page lists them). Lose
   and Restore: a note. Recover: room and note.
5. **Remove follows the lifecycle table everywhere**, including a device without any
   record (`None → REMOVED`), as the bulk remover does. The admin form's "localise it
   first" refusal is deleted: both device pages offered a button the form then refused.
6. **After a state change the user lands on the assets device page**, as after Order.
   A screen that sends users to the device page's forms or to Order passes
   `?back=<its URL>` to get them back; the inventory search does, so its users stay in
   their workflow and need no `core.view_device`. Move and Lend/Return keep their own
   landing pages. (`?next=` already carries an index querystring in the frontend, hence
   `back`.)
7. **Recover picks its room in a searchable select**, not the Move module: recovering
   stays a separate act with its own permission (`lifecycle.LOCALISING_MOVES`).
8. **State badges in the frontend link to the device page**, only for users with
   `core.view_device`; without it the badge has no link. The admin's badge links stay
   in the admin; the inventory's room badge keeps opening its room inventory.

## Alternatives considered and rejected

- Drop the `is_staff` check in `_set_state.html` only: the admin would still refuse
  non-staff users.
- Let the admin add-forms check the transition permission: new admin code, for an admin
  that is being phased out.

## Progress

- [x] 0. This document
- [x] 1. Lose, Remove, Restore, Recover on the assets device page; Remove aligned
- [x] 2. The inventory device search uses the frontend flows
- [x] 3. Inventory search: state badges link to the device page; state changes return to the search (`?back=`)
- [x] 4. Docs (`berechtigungen.md`) and NEWS
- [x] 5. The admin's device page opens the frontend screens; the record admins add nothing
- [x] 6. Delete the admin code that only served the record add-forms
