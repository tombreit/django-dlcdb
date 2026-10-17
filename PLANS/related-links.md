<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Related links: open or add the object a select points to

**Status:** implemented (steps 0–9, 2026-10-15 to 2026-10-16). This file now holds only what is
still open. An item that is picked up gets its batch here, or a plan of its own.

**The full plan** (design, decisions, the merge request review, pitfalls, what was decided during
implementation) is in the earlier versions of this file: `git log -p -- PLANS/related-links.md`.
The last full version is the parent of the commit that shrank it.

## What exists

- **One return parameter:** a link that opens a page passes the page it is on as
  `?next=<local URL>`, read with `theme.navigation.get_redirect_url`, as Django reads it.
- **Buttons next to a form's select** (`theme/related.py`, `theme/widgets.py`,
  `theme/assets/js/related-links.js`):
  - ✎/👁 opens the selected entry and + adds one, gated by the related model's own `view_`,
    `change_` and `add_` permissions;
  - an app registers its detail and add pages in `AppConfig.ready()` with
    `register_related_pages`;
  - the add page returns to the form with `<next_field>=<new pk>`, and the form preselects it.
- **Duplicate check on the add pages** (`theme/similar.py`): a name identical after normalization
  is refused, and similar names are listed while typing, as a hint only.

## Decide first

- **Who may see the duplicate lists** (merge request review, 2026-10-16).
  - The add views need only `add_*`. A user with only `core.add_person` sees existing persons'
    names in the "already exists" message and in the lists, deactivated persons included.
  - The "start of a name" rule with a two-letter minimum lets such a user step through the
    table.
  - Proposal, not decided: without the model's `view_*` permission, the add page still refuses
    an identical name but names no entry, and lists nothing while typing. That is a few lines in
    `theme/similar.py` plus a test.

## Ideas

1. **Read-only pages link related objects,** like the admin's read-only fields
   (`AdminReadonlyField.get_admin_url`). Without the change permission, the device detail page
   shows manufacturer, device type and supplier as plain text (its header and read-only card in
   `assets/devices/detail.html`), and so does the device list. The registry already knows where
   they lead and who may open them.
2. **A + in the person picker** (`theme/includes/_picker.html`), for contact person and borrower.
3. **Organisational units and smallstuff things** have no frontend pages
   (`PersonForm.organizational_unit`, `AssignedThingsForm.thing`). Once they do, registering them
   is enough.
4. **`lend.html`'s own unsaved-input check** (the script around `#lend-form-return`) could move
   onto the shared one in `related-links.js`.
5. **Delete links,** if delete views come. Then the admin's rule applies: no delete link when the
   FK's `on_delete` is CASCADE.
6. **Every link that opens a detail page passes `next`:** the dashboard search, the related lists
   on the room and person pages, and the device page's state-change links, so that a state
   change returns to the device page with its own `next`.
7. **The duplicate check on renames** on the detail pages (only adds are checked): only when the
   name changes, and excluding the entry itself.
8. **A merge tool for existing duplicates** (Procom / procom / pro-com in production).
   `udb_sync._merge_duplicate` shows how: it moves the reverse relations, then deletes.
9. **"Add “<typed text>”" in TomSelect's empty search result,** opening the add page with the
   name prefilled.
10. **Reactivating a deactivated match from the frontend.** The duplicate check refuses the name
    of a deactivated entry, and neither the select nor its page shows that entry.
