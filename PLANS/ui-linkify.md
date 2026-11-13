<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# UI linkify: link the objects the frontend names; a clearer device state card

**Status:** batch 2 done (links in templates), branch `ui-linkify`, 2026-11-13. This is a living document.

## Why

The frontend names rooms, persons, tenants, master data and devices in many places as plain text,
and the flash messages after a save name the object without linking it. The device page's
"Current state" card (`assets/devices/includes/_sidebar.html`) is the page's main component, but
it looks cramped: a small badge, a `<br>`, the room with an `ms-1` indent, and the page's main
action ("New state") is a `btn-sm`.

Goal: link a named object where a reader would plausibly go next. Leave it plain where a link would
be nested in another link, point to the page itself, drop unsaved input, or only classify a row.
Redesign the state card in the existing `card-filled` / `fact-list` language.

## Decisions taken

1. **The header's state badge on the device page becomes `d-lg-none`.** On desktop the sticky state
   card shows the state. On mobile the card sits below the long form, so the header badge stays
   the early cue. This resolves the DECISIONS follow-up "the state badge appears twice".
2. **Master data (type, manufacturer, supplier) is linked on detail pages only.** In list columns it
   classifies a row, and the filterbar already filters by it. Rooms, persons, tenants and devices
   are linked in lists too.
3. **A message links its object only when the redirect leaves that object's page:**
   - linked: the "… was updated" messages, "tenant created", licence saved/added, and the rooms a
     rename skipped;
   - plain: "created", "ordered" and "recorded", which land on the object's own page, or on a form
     with unsaved input.
4. **No link where leaving the page drops unsaved input**: the room in the lending return flow
   (`lending/lend.html`).
5. **Template links go through one include,** `theme/includes/_object_link.html`.
   - It takes `obj`, `url_name`, `perm` and an optional `label`.
   - It links only for a user with the page's view permission, and never to a soft-deleted
     object, whose page answers 404.
   - It passes the current page as `?next=`.
   - It is no template tag.
6. **Message links go through the existing `core/utils/links.py`** (`obj_link`, `linked_message`).
   - A `detail_url(obj)` finds the page: the model's `get_absolute_url()`, or a dict keyed by
     `_meta.label_lower`. The dict holds URL names as strings, so core still imports no app.
   - The journal's subject link uses it too.

## Alternatives rejected

- **`get_absolute_url` on more core models:** presentation stays out of core models (AGENTS). The two
  existing ones (Device, ImporterList) stay.
- **A template tag or filter that links any object:** the project has no custom tags.
- **`theme.related`'s registry for the message links:** core may not import theme.
- **Inline `{% if perms… %}<a>…{% else %}…{% endif %}` at every new site:** about five lines per
  site, and the soft-delete and `next` rules would be repeated each time. The existing inline links
  stay as they are.
- **A flag on `_state.html` for the device list's mobile copy:** moving that copy out of the
  stretched-link wrapper is enough.
- **Replacing the remaining admin links in frontend templates here:** reported as a follow-up.

## Batch 1: the state card

Three variants were rendered as screenshots (light and dark, desktop and 390px wide, INROOM, LENT
and LOST); the user picked B, built in its refined form B′:
- **Rejected:** A, the icon square tinted in the state colour, which almost disappears in dark mode;
  C, the title "Current state" over a large state badge, which says nothing new and is loud.
- **B′:** the header's icon square is a solid tile (`text-bg-{c}`) with an icon per state
  (`STATE_ICONS` next to `STATE_COLORS` in `theme/lifecycle_display.py`). The `<h2>` is the state
  name, with "Current state:" as visually-hidden text.
- **The card body.** The card gets its own markup instead of the list snippet `_state.html`: a
  `fact-list` with these rows:
  - Lender (link to the person page; "Person" outside LENT);
  - Room (link);
  - Lending: the period, linked to the lending (`lending_url`); LENT only. B's separate "Show this
    lending" line read as an external link;
  - Since (the active record's `created_at`; not for LENT);
  - Note (if the active record has one).
- **"New state"** becomes a full-width `btn btn-primary` of regular size: `dropdown d-grid`, menu
  `w-100`.
- **`_state.html`** becomes the device list's snippet only. Its `lending_url` branch goes; room and
  person become links (through the include, created in this batch).
- **The device list's mobile copy** of the state moves out of the stretched-link wrapper, so its
  links can be clicked.
- **The header badge** gets `d-lg-none` (decision 1).

### Decided during implementation

- **An INROOM record can carry a person** (a relocate keeps a licence's person), so the row is
  labelled "Person" there and "Lender" only for LENT.
- **Dates are ISO** (`SHORT_DATE_FORMAT`), like the rest of the frontend.
- **Icons:** ORDERED `bi-cart3`, INROOM `bi-door-open`, LENT `bi-person-check`, LOST
  `bi-question-circle`, REMOVED `bi-archive`; no active record `bi-activity`.

## Batch 2: links in templates

The include from batch 1, used for:
- the device list: tenant;
- the device page's read-only card: type, manufacturer;
- the record page: type, manufacturer;
- the record list: room, person;
- the lending list: person, room;
- the person page's lendings: room. The `blocktranslate` is split the way the room changes already
  split "from" / "in" + link;
- the room page's changes: the person in "Lent to", split the same way;
- the licence list: the licence name, to its form;
- the import list, the import page and the journal entry: tenant.

### New msgids from batch 2 (for the po files)

- `"in room"` and `"In room"`, context `"person lending"`; they replace `"Due {{ due }}, in room
  {{ room }}"` and `"In room {{ room }}"`. `"Due {{ due }}"` stays.
- `"Lent to"`, context `"room change"`; it replaces `"Lent to {{ person }}"` in that context.

## Batch 3: links in messages; retire the plan

- **`core/utils/links.py`:**
  - `detail_url(obj)`; `obj_link` uses it;
  - the module docstring says `str.format`, not `%`;
  - the journal's `_subject_url` uses `detail_url`.
- **Messages switch to `linked_message`,** with `{name}` placeholders. The msgids change; the po
  files are the maintainer's:
  - device, master data, room, person and tenant updated;
  - tenant created;
  - licence saved and added (now translatable);
  - the rooms that kept their number in a rename (`format_html_join`).
- **Tests:** `core/tests/test_links.py` for the new models and soft-deleted objects; one view test
  for the link in a "was updated" message.
- **Retire:** what still holds goes into `DECISIONS.md`, one line goes into `NEWS.md`, and this
  file is deleted.

## Deliberately not linked

- **The page's own object:** `<title>`, headings, the device page's header meta, the tenant delete
  text.
- **Inside another link or a clickable card:**
  - picker option cards;
  - dashboard search rows;
  - filterbar chips;
  - `state_btn_group.html`;
  - every list's stretched first column, including the device teaser's manufacturer.
- **Print and slips:** `lent_sheet.html` (also stored in the DB), `lent_checklist.html`,
  `print_base.html`, the QR printout, the inventory report.
- **No page, or history only:** users, inventories, organisational units, smallstuff things, field
  history values.
- **Messages:**
  - lifecycle errors, which are shown on the device page;
  - the HR contract warning, which is built in the model;
  - the duplicate-name errors, whose "Use this one" list already links.

## Pitfalls

- **Breaking a translated sentence around a link changes its msgid.** Split only where the word
  order allows it, as the room changes already do.
- **A link inside a stretched-link area can't be clicked:** the overlay covers it.
- **The include's `next` is `request.get_full_path`.** That is right for fragments paged through
  their page's own URL (device list, room changes). It is wrong for a fragment with a URL of its own.

## Open follow-ups

- **Admin links in frontend templates.** The inventory device search shows them to non-staff users
  too:
  - `inventory/partials/device_search_htmx.html`
  - `inventorize_room_detail.html`
  - `room_qrcodes_detail.html`
  - `notifications/index.html`
  - `lending/lend.html`
  - `licenses/form_partial.html`
- **Named objects on the inventory screens.** Their row markup is duplicated in `inventorize.js`.
- **The device on the notifications list.**
- **The import summary's "saved log".**
- **`obj_link` checks no permission:** the room in a relocate message can lead to a 403.

## Progress

- [x] Batch 0: this plan
- [x] Batch 1: the state card (variant B′)
- [x] Batch 2: links in templates
- [ ] Batch 3: links in messages; retire the plan into DECISIONS.md
