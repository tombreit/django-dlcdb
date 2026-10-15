<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Visual polish: typeface, lighter detail pages, dashboard

**Status:**
- implemented 2026-10-15:
  - batch 1, the typeface;
  - batch 2, `card-filled` sections on the device, record and lending pages;
  - batch 3, the other detail pages;
  - batch 4, the dashboard;
- planned 2026-10-15, from the follow-ups:
  - batch 5, read-only lists;
  - batch 6, the page headers of the lending and import detail pages;
  - batch 7, the last plain cards;
  - batch 8, translated model names;
  - batch 9, icons;
  - batch 10, identifiers in Plex Mono.

What is left is under *Open follow-ups*. *Identifier glyphs* answers the question of another
typeface. This is a living document.

## Why

The `redesign` branch (one WIP commit from 2026-09-12, 234 commits behind main) went too far:
- a sidebar app shell;
- a 14px base and 32px controls;
- a second CSS bundle behind a cookie switcher.

This round takes only the low-hanging fruit, inside the classic theme and Bootstrap 5.3, and keeps
the template markup as it is.

1. **Typeface.**
   - The build copies only Inter's latin subset (`build:theme:fonts`). Ł, ř, ş and ễ, and all
     Greek and Cyrillic letters in guests' names, fall back to a system font in the middle of a
     word.
   - The printed lending slip uses plain `sans-serif` (`frontend/admin/scss/print.scss`).
2. **Detail pages are boxes in boxes.**
   - The device edit page has 8–9 cards. Each has an outline, a shadow and a header rule.
   - Picker cards sit inside these cards.
3. **The dashboard is inconsistent.**
   - Tiles, search groups and charts each have their own card style.
   - A tile value is an integer, a "lent / total" string, an `Inventory` object, or three
     journal counts.
   - A count of 0 gets the singular label.
   - The charts use Roboto, their own palette and hardcoded German labels. In dark mode their
     text is dark on dark.

## Design

### Tokens

- **Type**
  - IBM Plex Sans Variable for everything: 400 for text, 500 for labels, 600 for headings.
  - IBM Plex Mono 400/500 for identifiers (`.font-monospace`): device IDs, serial numbers,
    UUIDs.
  - Tabular figures app-wide: Plex Sans's default figures already are (see *Decided during
    implementation*).
  - The base size stays at 16px, and Bootstrap's type scale stays as it is.
- **Colour**
  - The primary stays indigo `#4f46e5`.
  - States keep Bootstrap's contextual colours from `theme/lifecycle_display.py:STATE_COLORS`.
    The charts use them too.
  - The slate identity tile `#0f172a` stays.
- **Surfaces**
  - Page: `--bs-body-bg`.
  - Section: a panel in `--bs-tertiary-bg` with `--app-radius-lg`. It has no border and no rule.
  - Collapsed section on hover: `--bs-secondary-bg`.
  - Section icon: a 2rem square in 10% primary (25% in dark mode), with the icon in primary
    (`--bs-primary-text-emphasis` in dark mode).
- **Layout:** unchanged. The top navbar, `.container` and the `col-lg-8` / `col-lg-4` split all
  stay.

### Principles

1. **A border marks something you act on:** an input, a button, a picker item, a dashboard tile.
   A group is a tinted panel, not an outlined box.
2. **Colour means state.** Primary is reserved for actions, links and section icons.
3. **Bootstrap first.**
   - The `.card` component stays the blueprint for a section.
   - Changes go through Sass variables and the card's own `--bs-card-*` custom properties.
   - Each section gets one semantic modifier class.
   - No markup restructuring, no `{% if %}` style branches, no template tags.

### Detail page

     [▣] IT-04711                                  [← Back]
         Dell Latitude 7440   Laptop   ● In room

     ╭──────────────────────────────────╮ ╭──────────────────╮
     │ [▤] Identification               │ │ [~] Current state│
     │ IT ID            Inventory ID    │ │ ● In room        │
     │ [IT-04711    ]   [5100023    ]   │ │ [New state ▾]    │
     ╰──────────────────────────────────╯ ╰──────────────────╯
     ╭──────────────────────────────────╮ ╭──────────────────╮
     │ [▤] Manufacturer and model       │ │ [◷] Trail        │
     │ [Dell  ]  [Latitude ]  [CN0O1]   │ │ Records history  │
     ╰──────────────────────────────────╯ ╰──────────────────╯
     ╭──────────────────────────────────╮
     │ [▤] Procurement                ⌄ │   collapsed: a tinted bar
     ╰──────────────────────────────────╯
     [Save changes]  [Cancel]

     Light grey panels on the white page, no borders; the inputs stay white and outlined.

### Dashboard

     Device Life Cycle Database
     [ Search …                                                    ]

     Needs attention
     ┌───────────────┐ ┌──────────────┐ ┌───────────────┐ ┌───────────────┐
     │ ⏰ Overdue    │ │ ? Lost       │ │ ▤ Journal 30d │ │ ✓ Inventory   │
     │ 3             │ │ 12           │ │ 0    2    5   │ │ 64 %          │
     │ (warning tone)│ │              │ │ crit err warn │ │ ▓▓▓▓▓▓░░░ 2026│
     └───────────────┘ └──────────────┘ └───────────────┘ └───────────────┘
     Stock
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ Devices  │ │ Lendings │ │ Rooms    │ │ Types    │ │ Licences │ │ Smallst. │
     │ 1284     │ │ 41       │ │ 212      │ │ 38       │ │ 96       │ │ 310      │
     │          │ │ of 120   │ │ 7 w/notes│ │          │ │          │ │          │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘

     ╭ Devices by state ─────────────────╮ ╭ Most deployed types ─╮
     │ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ 355               │ │ ▒▒ Printer       34  │
     │ ▄ 11                              │ │ ▒▒ Label printer 32  │
     ╰───────────────────────────────────╯ │ ▒  Mouse         32  │
     ╭ Device history ───────────────────╮ │ …  (top 15)          │
     │      ___/‾‾‾‾\___                 │ │                      │
     │  __/                              │ │ All 23 device types  │
     ╰───────────────────────────────────╯ ╰──────────────────────╯

## Decisions taken

1. **Classic theme only:** no second bundle and no switcher. Each batch is small and revertible.
   The `redesign` branch is a quarry: its `next/_fonts.scss` is reused, and the rest stays there.
2. **IBM Plex Sans Variable** (`@fontsource-variable/ibm-plex-sans`).
   - All six subsets ship: latin, latin-ext, vietnamese, greek, cyrillic and cyrillic-ext.
   - Each is an `@font-face` with a `unicode-range`, so a page downloads only the subsets it uses.
     All six together are about 170 KB.
   - **IBM Plex Mono** (`@fontsource/ibm-plex-mono`, latin and latin-ext, 400 and 500) is used for
     identifiers.
   - The fonts are self-hosted as today, not loaded from Google Fonts, for privacy and for offline
     installs.
   - Inter goes.
3. **No web font covers all of Unicode.**
   - Arabic, Hebrew, CJK, Devanagari, Georgian, Armenian and other scripts fall through the stack
     (`system-ui, …, "Noto Sans", sans-serif`) to the OS fonts.
   - Browsers fall back per character, so these names still render correctly, in another design.
4. **The printed lending slip uses Plex too.**
   - `print.scss` imports the same `_fonts.scss`, with `$font-dir` pointing at the theme's fonts.
   - This follows the pattern of `$bootstrap-icons-font-dir` in
     `frontend/admin/scss/_variables.scss`.
5. **`card-filled`: a modifier on Bootstrap's `.card`** (the user's direction: keep the card
   markup, add one class).
   - **History:**
     - The first version (`card-flush`, 2026-10-15) dropped the box entirely: a heading, a
       hairline and a 1rem title.
     - The user found the sections "barely recognizable" and the toggle icons too small.
     - Two variants were rendered on the device and lending pages:
       - V1 kept the hairline, with a bigger title;
       - V2 made filled panels.
     - The user chose V2 (Material 3's "filled card", Apple's grouped settings lists).
     - The modifier was renamed with it: Bootstrap's `-flush` means "no borders, no rounded
       corners, edge to edge with the parent", which a rounded, padded panel is not.
   - **Markup:** a section card only gains the class (`class="card card-filled mb-3"`). Its
     `card-header`, icon, `h2` and `card-body` stay as they are.
   - **Card variables:** in Sass, `.card-filled` sets the card's own custom properties:
     - `--bs-card-bg: var(--bs-tertiary-bg)` and a transparent `--bs-card-cap-bg`;
     - `--bs-card-spacer-x` and `--bs-card-cap-padding-x`: 1.25rem;
     - `--bs-card-cap-padding-y`: .875rem;
     - border radius `--app-radius-lg`.

     The card itself gets `border: 0`, and the header has no rule.
   - **Header rules:**
     - `.card-filled > .card-header` sets one title style: 1.125rem, semibold, icon and title
       side by side.
     - Anything else in a header, such as a count or a "Manage" link, stays body text
       (`> :where(a, span, small)`).
     - The first icon sits in a tinted 2rem square.

     So the three header idioms render the same without touching them:
     - `h2.device-card-title`, on the device and record pages;
     - `h2.h6 mb-0` with a `text-primary` icon, on 16 other templates;
     - plain text after an icon, on the lending page.
   - **Collapsible sections:**
     - These are `<details>` with `<summary class="card-header">`, or a Bootstrap collapse with
       `<button class="btn card-header">` (lending).
     - The trailing `.card-caret` is 1.25rem. It rotates on `details[open]` and on
       `[aria-expanded="true"]`.
     - Collapsed, the section is a tinted bar that darkens on hover.
   - **Nested object cards stay cards** (principle 1), because they are things you pick: the picker
     items in `_person_list_item.html` and `device_picker/_item.html`. The modifier only sets the
     filled card's own custom properties. A nested `.card` resets them.
   - **No global `$card-*` override:** that would also restyle the dashboard tiles and picker
     items.
6. **The side column is a stack of panels, like the main column.**
   - `_detail_base.html` wraps the sidebar block in `<aside class="detail-aside">`.
   - The read-only pages outside that frame wrap their side column the same way.
   - The aside has no style of its own; it is the hook for the device page's sticky column.
   - Batch 2's first version tinted the aside as one block. That became redundant once every
     section is a panel.
7. **The primary colour stays indigo** (user decision, 2026-10-14).
8. **`dl` lists keep their markup.**
   - The `.device-meta` labels lose their uppercase. This is a Sass change only.
   - The different column ratios (`col-sm-3/9`, `4/8`, `5/7`, `6/6`) are unified in batch 5
     (decision 11).
9. **Dashboard**
   - **Two groups of tiles,** each under an `h2`:
     - *Needs attention*: overdue lendings, lost devices, journal problems and the active
       inventory;
     - *Stock*: devices, lendings, rooms, device types, licences and small stuff.
   - **One tile anatomy:** icon and label, then the value, then an optional caption, all
     left-aligned. Tiles stay bordered cards, because they are links.
   - **The value is always a number:**
     - lendings show the lent count, with the caption "of N lendable";
     - inventory shows the done % from `Inventory.get_inventory_progress(tenants=…)`, with a
       thin `.progress` bar and the inventory's name as caption;
     - the journal keeps its three level counts.
   - **Notes:** the note badge becomes a caption ("N with notes"). The tile still links to the
     note-filtered list, as today.
   - **Overdue tone:** a non-zero Overdue tile takes Bootstrap's warning tokens
     (`--bs-warning-bg-subtle`, `--bs-warning-border-subtle`, `--bs-warning-text-emphasis`), which
     work in light and dark mode.
     - Lost gets no tone. It counts every loss ever recorded, so it is rarely zero.
   - **Plurals:** every count except 1 gets the plural label. Today 0 gets the singular.
   - **Filled cards:** the search result groups and the chart cards gain `card-filled`.
   - **Charts:**
     - Plex font.
     - Record-type colours from `STATE_COLORS`, as hex values of Bootstrap's palette, kept next to
       the chart code.
     - Translated record-type labels.
     - "Devices by location" becomes "Devices by state", which is what it shows.
     - Axis text follows `--bs-body-color` in dark mode.
     - Load the `dataviz` skill before changing them.
   - **Most deployed device types: a ranked list, not a chart.** User decisions, 2026-10-15,
     after the Plotly bar chart grew far too tall with real data:
     - the top 15 (`DEVICE_TYPE_RANKING_SIZE`), one compact row per type: icon, name, count, and
       a bar behind the row scaled to the count;
     - each row links to the device list filtered by that type
       (`assets:device_index?device_type=<pk>`);
     - when the list is cut, "All N device types" links to the device type list sorted by
       device count (`?ordering=-assets`);
     - a device counts unless its active record is REMOVED or it is soft-deleted. The linked list
       also shows removed devices; the user accepted that;
     - it sits in a right column (`col-lg-4`) beside "Devices by state" and "Device history",
       which stack on the left (`col-lg-8`).
10. **NEWS:** no entry per batch. At the end, one line is offered in the summary: this is polish
    (AGENTS.md).
11. **Read-only `dl` lists: one layout per column** (batch 5).
    - **Main column:** the label sits beside the value, `col-sm-4` / `col-sm-8`, with
      `text-secondary fw-medium` labels. Every page but the lending page does this already.
    - **Side column:** the label sits above the value, as on the device and record pages today.
      - Today the side column uses three ratios: `4/8` (record data), `5/7` (HR API data) and
        `6/6` (tenant usage). The values of two stacked panels start at different offsets.
      - At about 270px, long German labels wrap at any ratio, e.g. "Benutzer mit Zugriff auf
        diesen Mandanten" or "Voraussichtlicher Check-Out". UUIDs and e-mail addresses break
        across lines.
      - Stacked, both get the full width. The cost is height: the HR API data panel grows from
        about 350 to 600px.
      - Rendered with injected CSS on the scratch DB, side by side with today's look
        (2026-10-15).
    - **`.device-meta` becomes `.fact-list`:** read-only facts about an object, label above
      value, a hairline between facts. It moves to its own partial, since persons, tenants and
      the record data include use it too.
      - It styles bare `dt`/`dd` pairs as well as the device page's `div`-grouped ones.
      - So the device and record templates only change the class name.
12. **The lending and import detail pages get the detail pages' header band** (batch 6):
    `h1.h3`, a muted meta line under it, and actions plus the back button on the right
    (`_detail_base.html`).
    - **Lending:**
      - the picker hint moves into the meta line;
      - "Admin view" and "Back to overview" sit on the right, both at the default size;
      - the back button goes through `_back_link.html`.
    - **Import detail, re-checked:** the "small grey 'Import' line" was an artefact of the
      scratch DB.
      - The title is `str(ImporterList)`, the stored file path. It was empty for the seeded
        import, which has no file. On real data it reads `imported_csv/<name>.csv`.
      - The title becomes the file's name (`ImporterList.file_name`), or "Import without file".
      - The import list's row link uses the same name: today it shows the folder too, and it is
        empty without a file.
13. **The last plain cards become filled panels** (batch 7):
    - the subscription form on `notifications/index.html`, which gets a header icon and an `h2`;
    - the intro card on `dataexchange/import.html`.

    Two cards stay as they are, deliberately:
    - the login form card: a single form on an empty page;
    - the relocate page's step cards: their border carries the step's done state (principle 1).
14. **Model names are translatable** (batch 8).
    - **`Device`** was reported: its tile reads "Devices" in the German UI.
    - **Its siblings in `core`** need the same one-line fix, and their msgids exist, so nothing
      regresses in the German UI:
      - `Person` and `Note`, hardcoded in German ("Personen", "Notiz");
      - `Record`, `Attachment` and `Link`, hardcoded in English.

      Strike them if `Device` alone is wanted.
    - **Migration:** one `AlterModelOptions` migration, with no schema change.
    - **Left out:**
      - `RoomReconcile` ("Raum-Abgleich"): its msgid would be new, so the German UI would show
        English until it is translated;
      - other apps' names: they show only in the admin.
15. **One icon per entity** (batch 9).
    - **Device:** `bi-pc-display` wherever the icon stands for the device: the navbar, the
      tiles, the search group, the section headers, and the default of `DeviceType.icon_class`.
      - `bi-upc` stays where it marks a number, e.g. the ID line of a picker item.
      - `bi-upc-scan` stays on the *Identification* section.
    - **Lost:** `bi-question-circle`, the icon the inventory uses for a device not found yet,
      instead of Records' `bi-stack`.
16. **Batches 5–10 are committed by Claude**, one commit per batch (user's permission,
    2026-10-15).
    - The message is one self-explanatory line, "Visual polish, step N: …".
    - The batch's box is ticked in the same commit.
    - `/verify` runs before each commit.
    - The plan update is committed first, once the user has reviewed it.
17. **Identifiers are set in Plex Mono, in inputs and on the slip too** (batch 10; user,
    2026-10-15, see *Identifier glyphs*).
    - **Rule:** a code that is read or typed character by character is set in Plex Mono, whose
      zero is dotted:
      - IT ID, inventory number and serial number;
      - MAC addresses and encryption keys;
      - room number and device type prefix.

      The read-only views already set the first group, the room number and the prefix in
      `.font-monospace`. MAC addresses and keys are in mono nowhere yet.
    - **Form inputs:** `add_bootstrap_classes` keeps a class the form declares, with Bootstrap's
      class first. The forms declare `font-monospace` in `Meta.widgets`.
    - **The slip:**
      - `print.scss` has no Bootstrap. It gets its own `.font-monospace` rule with the Plex Mono
        stack, so the slip templates use the frontend's class name.
      - The checklist's inline `monospace` becomes the same stack.
      - Glyphs outside Plex Mono's latin range fall back per character, as they do today.
    - **Plex Sans stays from Fontsource.** IBM's own package is not used: it reports to IBM on
      install in CI and in containers, it costs bytes, and it is a 0.x package.

## Progress

Batches 1–4: after each batch, stop so the user can commit it. Batches 5–10: Claude commits each
batch (decision 16).

- [x] **0. This document**
- [x] **1. Typeface** (decisions 2–4). No template changes.
  - Packages:
    - `npm install -D @fontsource-variable/ibm-plex-sans @fontsource/ibm-plex-mono`;
    - `npm uninstall @fontsource-variable/inter`.
  - `package.json`, `build:theme:fonts`: `mkdir -p`, then copy the six Plex Sans
    `*-wght-normal.woff2` and the four Plex Mono files (latin and latin-ext, 400 and 500).
  - New `dlcdb/theme/assets/scss/_fonts.scss`, starting from
    `git show redesign:dlcdb/theme/assets/scss/next/_fonts.scss`. Add to it:
    - the Plex Mono faces;
    - `$font-dir: "../fonts" !default`.
  - `theme.scss`:
    - the Inter `@font-face` becomes `@import "_fonts"`;
    - set `$font-family-sans-serif`, `$font-family-monospace` and `$headings-font-weight: 600`.
  - `frontend/admin/scss/print.scss`:
    - set `$font-dir: "../../../theme/dist/fonts"`;
    - `@import` `_fonts`;
    - replace `sans-serif` with the Plex stack.
  - Check Plex Sans's `tnum` feature, and how Plex Mono's zero looks next to an O. Done; see
    *Decided during implementation*.
- [x] **2. `card-filled`; device, record and lending pages** (decisions 5, 6 and 8)
  - New `dlcdb/theme/assets/scss/_cards.scss` with `.card-filled`, `details.card-filled` and
    `.card-caret`. `theme.scss` gets its import line, the only line a second batch touches there.
  - `_device-page.scss`:
    - drop `.device-card*` and `.device-caret`;
    - drop `.device-sidebar`; its sticky position moves to `.device-page .detail-aside`, so only
      the device page sticks;
    - `.device-meta` labels lose their uppercase.
  - `theme/_detail_base.html`: the `<aside class="detail-aside">` wrapper, and its block docs.
  - Class-only edits:
    - in `assets/devices/detail.html`, `devices/includes/_form_fields.html`,
      `devices/includes/_sidebar.html`, `devices/history.html` and `assets/records/detail.html`;
    - `device-card` → `card-filled` and `device-caret` → `card-caret`;
    - `device-card-title` and the `device-sidebar` wrapper go.
  - Lending (`lending/lend.html`, all three flows), moved here from batch 3 at the user's request:
    - `card-filled` on its six cards;
    - `card-caret` on the two collapse chevrons;
    - the collapse headers lose their `<span>` wrapper and `justify-content-between`, so the icon
      is the header's first child;
    - the variant-less `div.alert` around each date field renders only when the field has an
      error (`class="alert alert-warning mb-0"`), so the fields line up with the section;
    - the dead `border-success` on the return card goes; its `bg-success-subtle` header stays as
      the flow's emphasis.
  - The Bootstrap collapse markup stays, so the assertions in `lending/tests/test_views.py` hold.
- [x] **3. The other detail pages gain the modifier**
  - These templates add `card-filled` to their section cards:
    - persons: `detail.html`, `includes/_form_fields.html`, `_lendings.html`, `_licences.html`,
      `_smallstuff.html`;
    - rooms: `detail.html`, `includes/_form_fields.html`, `_changes.html`;
    - masterdata: `detail.html`, `_form_fields.html`;
    - tenants: `detail.html`, `includes/_form_fields.html`;
    - journal: `detail.html`, `cleanup.html`;
    - `dataexchange/importer_detail.html`;
    - `theme/includes/_audit_data.html`;
    - `licenses/history.html`, the twin of the device field history.
  - Rooms: `card-collapse` → `card-filled` and the inline `<style>` goes. The caret already was
    `card-caret`.
    - Test `rooms/tests/test_rooms.py` asserts the `<details>` class string and is updated.
  - `_cards.scss`: secondary header content stays body text.
- [x] **4. Dashboard** (decision 9)
  - `dashboard/views.py`: the tile dicts get `value`, `caption`, `tone` and `group`.
  - Also: `dashboard/includes/_tile.html`, `dashboard/index.html`,
    `theme/assets/scss/_dashboard.scss`, `dashboard/stats.py` and `dashboard/tests/test_tiles.py`.
    The test asserts the tile's class string.
  - Plotly writes the text `fill` as an inline style, so dark mode needs one scoped override in
    `_dashboard.scss`.
  - Follow-up commit, after batch 4 had landed: the device type chart became the ranked list of
    the most deployed device types (decision 9).
- [x] **5. Read-only lists** (decision 11)
  - New `dlcdb/theme/assets/scss/_fact-list.scss` with `.fact-list`, moved from `.device-meta`
    in `_device-page.scss`.
    - The separator rule covers `> div + div` and `> dd + dt`.
    - `theme.scss` gets its import line.
  - Side column: `<dl class="row mb-0 small">` with `col-sm-*` and label utilities becomes
    `<dl class="fact-list">` with bare `dt` and `dd`:
    - `theme/includes/_audit_data.html`, used on the person, room, master data, tenant and import
      detail pages. The UUID keeps `font-monospace`;
    - the HR API data on `persons/detail.html`;
    - the usage on `tenants/detail.html`.
  - `device-meta` → `fact-list` in `devices/includes/_sidebar.html` and `records/detail.html`.
  - Main column: the *Lending details* list in `lending/lend.html` goes from `col-sm-3/9` to
    `col-sm-4/8`, with `text-secondary fw-medium` labels.
  - No test asserts these classes.
  - Screenshots:
    - person with HR API data, tenant, room, device, record;
    - lending return, for the main-column list.
- [x] **6. Page headers: lending and import detail** (decision 12)
  - `lending/lend.html`:
    - the header band;
    - the inline `<style>` with `.picker-option:hover` goes: `picker.css` loads in both branches
      of `extra_css`.
  - `dataexchange/models.py`: `ImporterList.file_name`, the base name of the stored file.
    `__str__` stays: the journal stores it as `object_repr`.
  - `dataexchange/importer_detail.html`: `<title>` and `h1` use the file name, with the fallback.
    The back button goes through `_back_link.html`.
  - `dataexchange/importer_index.html`: the row link uses the file name.
  - Tests in `dataexchange/tests/`:
    - the detail title and the list link show the file name without its folder;
    - an import without a file gets the fallback.
- [ ] **7. The last plain cards** (decision 13)
  - `notifications/index.html`: `card card-filled mb-4`, with the header
    `<i class="bi bi-bell"></i><h2>…</h2>`.
  - `dataexchange/import.html`: `card card-filled mb-4`.
- [ ] **8. Model names** (decision 14)
  - Read the docstring of `dlcdb/core/__init__.py` first (AGENTS.md).
  - `verbose_name` and `verbose_name_plural` through `gettext_lazy` in `core/models/device.py`,
    `person.py`, `note.py`, `record.py` and `misc.py`.
  - The migration comes from `DATABASE_URL=sqlite://:memory: ./manage.py makemigrations core`.
    `makemigrations --check` is clean afterwards.
  - `dashboard/search.py`: the comment about `Person`'s German verbose name goes. The explicit
    label stays, like the other sources' labels.
  - Test: under `translation.override("de")` the devices tile reads "Geräte". The compiled
    `django.mo` is in the repo.
- [ ] **9. Icons** (decision 15)
  - `theme/icons.py`: `core.device` → `bi bi-pc-display`, `core.lostrecord` →
    `bi bi-question-circle`.
  - `dashboard/search.py`: the device group's icon → `bi bi-pc-display`.
  - `theme/tests/test_icons.py` pins both.
- [ ] **10. Identifiers in Plex Mono** (decision 17)
  - `theme/forms.py`: `add_bootstrap_classes` merges a declared class instead of overwriting it.
    Its docstring says so.
  - `assets/forms.py`:
    - `DeviceForm.Meta.widgets`: `edv_id`, `sap_id`, `serial_number` and `mac_address` become
      `forms.TextInput(attrs={"class": "font-monospace"})`;
    - its three `Textarea`s (`extra_mac_addresses` and both encryption keys) gain the class;
    - `DeviceTypeForm`: `prefix`.
  - `rooms/forms.py`: `number`.
  - `frontend/admin/scss/print.scss`: `.font-monospace` with
    `"IBM Plex Mono", ui-monospace, monospace`.
  - `lending/includes/lent_sheet.html`: the serial number, the device and the inventory number in
    `<span class="font-monospace">`.
    - The DB-stored sheet templates include this file (starter: `lent_sheet_starter.html`), so
      the change reaches every profile that includes it.
  - `lending/includes/lent_checklist.html`: the inline `font-family` becomes the Plex Mono stack.
  - Inventory: `text-monospace`, a Bootstrap 4 class, becomes `font-monospace` (seven times).
    Bootstrap 5 dropped the old class, so these identifiers render in Plex Sans today. The files:
    `inventory/inventorize_room_detail.html` and `inventory/partials/device_search_htmx.html`.
    - The admin's `core/device/history_diff.html` keeps it: the admin is being phased out.
  - Tests:
    - new `theme/tests/test_forms.py`: a declared class survives, after Bootstrap's;
    - assets: the device form renders `form-control font-monospace` on `edv_id` and on a key
      field;
    - lending: the printed sheet wraps the inventory number in `font-monospace`.
  - Verify:
    - device edit and add, room edit, device type edit, the inventory room page;
    - the slip PDF: `CSS.getPlatformFontsForNode` shows Plex Mono on the identifiers, and a Greek
      or Cyrillic guest name still in Plex Sans.

Every batch:
- `npm run build`
- `ruff check . && ruff format --check .`
- `DATABASE_URL=sqlite://:memory: ./manage.py check`
- `DATABASE_URL=sqlite://:memory: .venv/bin/pytest .`
- `/verify` against a scratch DB, with screenshots of the batch's pages:
  - light and dark mode;
  - desktop width and 390px;
  - edit and read-only mode wherever a page has both.

Batch 1 additionally:
- Create persons named `Łukasz Żółkiewski`, `Nguyễn Thị Minh Khai`, `Σωκράτης Παπαδόπουλος`,
  `Владимир Ковалёв` and `Şahin Dvořák`, plus one Arabic and one CJK name for the OS fallback.
- Check which font renders each script.
- A latin-only page loads exactly one Plex Sans file.
- Print the lending slip for one of these guests.

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| A new `.panel` component with rewritten header markup (first draft of this plan) | Touches every card header in 21 templates. The `.card` blueprint plus one modifier gives the same look. |
| A page-level flag with descendant selectors (`.detail-page .card`) | It would also hit nested picker cards, and `:not(.card .card)` hides the rule. A modifier on each section card is explicit. |
| Global `$card-*` overrides | They would also strip dashboard tiles and picker items. |
| Div-grouped `property-list` for every `dl` | A markup rewrite of every read-only list, for little visual gain. |
| Reviving the redesign branch's `theme-next` bundle and cookie switcher | It exists only for side-by-side previews. Small batches in the classic theme are just as easy to revert. |
| Sidebar shell, 14px base, 32px controls, ink-black primary, borderless inputs | Layout experiments: the part of the branch that went too far. |
| "Soft panels" (white cards on a tinted page) or "hairline cards" | Panels would tint the whole page background; hairline cards keep the outlines. |
| Sections as a heading plus hairline (`card-flush`, batch 2's first version) | Rendered and rejected by the user: the sections were barely recognizable and the toggles too small. |
| V1: hairline sections with a bigger title and an icon square (Stripe dashboard, GitHub's settings "Subhead") | Rendered next to V2. Better, but on dense forms the hairline still separates sections only weakly. |
| Source Sans 3, Noto Sans, or Inter with all subsets | The user chose IBM Plex Sans. Noto and Inter would also stay generic. |
| Self-hosting Plex Arabic, Hebrew, Devanagari, Thai and CJK now | Large files for names that are rare today. The OS fallback renders them. |
| Google Fonts | Privacy, and installs without internet access. |
| A new primary colour | The user keeps indigo. |
| Rendering the charts in the browser from CSS variables | A bigger change. Server-side Plotly with theme hex values is enough. |
| Device types as a Plotly bar chart (batch 4's first version) | One bar per type with 10 or more devices: with real data far taller than its neighbours. |
| Device types as a compact Plotly bar chart (top 15, 12px bars) | Bounded, but no links, and its text needs the dark-mode overrides. |
| Device types as a treemap | Compact, but areas are hard to compare and small types get unreadable labels. |
| One `col-sm-5/7` ratio for every side-column list | Values line up, but long German labels still wrap, and the device and record pages keep their stacked list: two looks for the same thing. |
| A `.detail-aside dl` rule instead of a class on the list | A page-level descendant selector, rejected for the cards already. It would also have to fight the `row` grid. |
| Showing the import's file name through `ImporterList.__str__` | The journal stores `str()` as `object_repr`, so old and new entries would differ, and the admin would change too. |
| Another typeface for unambiguous identifiers | See *Identifier glyphs*: no face with the guests' scripts does better than Plex Sans. |
| IBM's `@ibm/plex-sans-variable` for a slashed zero app-wide | It reports to IBM on install in CI and in containers. It adds about 21 KB on a latin page, and it is a 0.x package. |
| Subsetting Google's full Plex Sans TTF ourselves, keeping `zero` | A Python build step next to the npm build. |
| A loop after `add_bootstrap_classes` in each form, adding `font-monospace` | The same lines in three forms. One change to the helper serves them all. |

## Open follow-ups

- **Primary colour:** indigo is kept for now. It is Tailwind's default, so it reads as generic.
- **Plex Sans for other scripts:** self-host Plex Sans Arabic, Hebrew and so on if names in those
  scripts become common.
- **Out of scope for this round:** list pages (`_index_base.html`), the filterbar, and one page
  header for index, detail and lending pages.
- **New msgids to translate:**
  - batch 4:
    - "Needs attention" and "Stock";
    - "of %(total)s lendable" and "%(done)s of %(total)s devices";
    - "Devices by state";
    - "Most deployed device types", "No deployed devices yet." and
      "All %(counter)s device type" / "All %(counter)s device types".

    The chart's state labels reuse the lifecycle labels, and the notes caption reuses the old
    badge's msgid.
  - batch 6: "Import without file";
  - batch 8: "Attachment", "Link" and "Links". "Attachments" and the other model names exist.
- **A wrong German plural:** "%(counter)s devices" is translated as "%(counter)s Geräten" (dative),
  so the import detail page reads "0 Geräten". This is a `.po` fix.
- **Other untranslated model names** (decision 14): `RoomReconcile`, and the admin-only names in
  dataexchange, inventory, lending, reporting and organization.
- **Charts have no table view:** the dataviz method asks for one per chart. Values are reachable
  through the labels, the hover tooltips and the linked lists.
- **Device detail:** the state badge shows twice, in the header and under *Current state*.
- **The admin keeps Roboto.** The admin is being phased out.

## Identifier glyphs

The question (2026-10-15): Plex Sans's zero has no inner mark. Is there a typeface that avoids
this?

**Decided (user, 2026-10-15):** Plex Sans stays, from Fontsource, and identifiers are set in Plex
Mono (way 1 below). This is batch 10, decision 17.

**Correction:** Plex Sans does tell `1`, `I` and `l` apart: `I` has slab serifs, `l` a tail and
`1` a base. The earlier follow-up claimed otherwise. Only the zero is ambiguous. It is narrower
than `O`, which helps only when both stand side by side.

**No other typeface does better.** Checked 2026-10-15:
- **Scope:** about forty popular faces were looked up in the Fontsource API. Eleven sans faces
  among them cover the guests' scripts (latin-ext, Vietnamese, Greek, Cyrillic).
  - They were rendered in Chromium from their Fontsource files.
  - Their features and glyph widths were read with fontTools.
- **The zero:** none of them marks it by default.
  - The Fontsource builds (from Google Fonts) also drop the `zero` feature of every one of them,
    Plex Sans's own included.
  - The faces that mark their zero by default cover Latin only, so they fail the guests
    requirement: Atkinson Hyperlegible Next (latin, latin-ext), B612, Luciole.
- **`1`, `I`, `l`:**

  | Face | What sets them apart |
  |---|---|
  | Fira Sans, Source Sans 3 | A tailed `l`, but a bare `I` |
  | Noto Sans | A serifed `I`, but a bare `l` |
  | Inter, Open Sans, Roboto Flex, Commissioner, Manrope, Geologica | Nothing: `I` and `l` look the same |
  | Alegreya Sans | Old-style figures: its `0` is a small `o` |

**Two ways to a marked zero without another typeface:**
1. **Plex Mono where identifiers are typed or printed** (taken; details in decision 17):
   - the inputs for identifiers and codes;
   - the device line of the lending slip.

   The lists and detail pages already set identifiers in Plex Mono (decision 2), and Plex Mono's
   zero is dotted.
   - The inputs get the class from their form, through `add_bootstrap_classes`, with no template
     change.
   - The slip's device line is in the file template `lent_sheet.html`, which the DB-stored sheet
     templates include.
2. **IBM's own build,** `@ibm/plex-sans-variable` (0.2.0, June 2025, from github.com/IBM/plex).
   - The same design, with the same 1025 glyphs as Google's build.
   - It keeps `zero` (slashed) and `ss04` (dotted), so `font-variant-numeric: slashed-zero` marks
     the zero wherever it is set: on identifiers only, or app-wide.
   - **Costs:**
     - **Telemetry.** Every `@ibm/plex-*` package runs `ibmtelemetry` on install
       (`postinstall`, with `@ibm/telemetry-js` as a dependency).
       - It reports anonymised dependency data to IBM, only in CI and in containers.
       - `container/Containerfile` runs `npm ci` in a container stage, so every image build
         would report.
       - The opt-out is `IBM_TELEMETRY_DISABLED=true` wherever npm installs. That runs against
         decision 2's privacy reasoning.
     - **Bytes:** 67 KB instead of 46 KB on a latin-only page, and 253 KB instead of 159 KB for
       all six files. Most of the extra is the width axis, which we don't use.
     - **Upkeep:**
       - it is a 0.x package, with no release since June 2025;
       - its file names contain spaces (`IBM Plex Sans Var-Roman-Latin1.woff2`);
       - IBM splits the font into Latin1/2/3, Greek, Cyrillic and Pi, so `_fonts.scss` and
         `build:theme:fonts` change;
       - its split files leave out 13 combining accents that its complete file has.

**Why Fontsource's Plex lacks the features.** The difference is in the delivery, not in the
font:
- Fontsource builds no fonts. It repackages the files the Google Fonts API serves.
- Google's source file (IBM Plex Sans 3.201, January 2025, in the google/fonts repository) has
  `zero` and `ss01`–`ss06`.
- The API strips them when it cuts the web subsets. Its latin file keeps only ccmp, dnom, frac,
  liga, numr and rvrn, exactly Fontsource's list.
- Fontsource's weight-only files also fix the width axis (75–100, the condensed cut) at 100%.
  That makes them smaller than the API's: 46 KB against 65 KB for latin.

**Recommendation, taken:** way 1. It extends an existing rule (identifiers in Plex Mono) to the
last places that miss it, and it needs no new font source.

## Pitfalls

- **Font paths are relative to the compiled CSS,** because Sass doesn't rewrite `url()`s.
  - `theme/dist/css/theme.css` needs `../fonts`.
  - `dist/admin/css/print.css` needs `../../../theme/dist/fonts`, set through `$font-dir`.
  - Fontsource's own CSS can't be imported for the same reason. Copy the `unicode-range`s from
    its `wght.css`.
- **A quoted `unicode-range` is invalid CSS.** Sass emits a quoted string as is, and browsers
  then drop the descriptor, so every subset claims every character. The redesign branch had
  this bug; `_fonts.scss` uses `unquote()`.
- **`build:theme:fonts`** had no `mkdir -p`. It only worked because `bs-icons` runs first (fixed in
  batch 1).
- **Stale font files:** `dist/fonts` still holds files from the redesign build
  (`ibm-plex-sans-*`, `theme-next.css`). They can hide a missing copy step, so empty it before
  checking batch 1.
- **Child selectors only:** style the modifier with `.card-filled > .card-header`, never with a
  descendant selector. Nested picker cards must keep their box.
- **List groups inside a filled card:** `list-group-flush` items keep `--bs-list-group-bg` (the
  body background), and their default hover tint is the panel's own colour.
  - Inside a filled card they are transparent, indented like the section text, and hover in
    `--bs-secondary-bg`.
- **Icon colours in dark mode:**
  - `--bs-primary-bg-subtle` is almost black in dark mode, and plain indigo is too dark on the
    dark panel.
  - The icon square therefore uses `rgba(var(--bs-primary-rgb), …)`, with the icon in
    `--bs-primary-text-emphasis` under `color-mode(dark)`.
- **A collapse button as `.card-header`:**
  - `.btn` brings its own font size, but the header rule (specificity 0,2,0) beats it.
  - `.btn` also brings a 1px transparent border, which shifts the lending icon by 1px.
- **Checking with `runserver --noreload`:** Django's cached template loader keeps the templates
  it has loaded. After editing templates, restart the server, or the page renders the old
  markup against the new CSS.
- **Sass 1.77 (pinned) crashes on `:where(:not(h2, .bi))`.** The error is "components may not be
  empty", in `@extend` handling: Bootstrap's `.small` extends `small`. Name the elements instead.
  A crashed build leaves the old `theme.css` in `dist/`, so check the build's exit code, not its
  output.
- **Utilities win over the modifier.** `!important` utilities in existing markup override it,
  e.g. `bg-success-subtle` on the lending return header. Check them visually rather than fight
  them.
- **Sticky aside:**
  - An element inside the aside can't stick, because the aside is exactly as tall as it is.
    Sticky goes on the aside itself.
  - Only the device page gets it. A taller aside would be cut off at the bottom.
  - The offset must clear the sticky navbar (57px). `top: 1rem` hid the aside's first section
    under it.
- **The wheel ships the collected static files** (`PLANS/pip-distribution.md`). New font files
  must land in `dist/fonts` through the npm build.
- **Plotly figures are built in Python per request:**
  - colours must be hex values;
  - labels are translated in the request's active language.
- **Lending slip templates are stored in the DB** and load `markdown_extras` by name. Batch 1
  changes only `print.scss`, not those templates.

## Decided during implementation

- **Batch 1, no `font-variant-numeric` rule.** All ten digits in Plex Sans have the same advance
  width (600 units), so its figures are tabular by default. Fontsource's subsets carry no `tnum`
  or `zero` feature anyway, only `ccmp`, `dnom`, `frac`, `liga` and `numr`.
- **Batch 1, Plex Mono's zero has an inner mark:** three contours, against two for `O`. Identifiers
  in `.font-monospace` (device ID heading, inventory and serial numbers in lists, UUID) are
  unambiguous.
- **Batch 1, `"Noto Sans"` in the fallback stack,** before `Arial`. It is the broadest system font
  on Linux desktops.
- **Batch 1, one range map for both families.** The Plex Mono subsets use the same `unicode-range`s
  as Plex Sans's latin and latin-ext.
- **Batch 1, checked in Chromium (2026-10-15)** with `CSS.getPlatformFontsForNode` on a scratch DB:
  - a page with German text only (device detail) loads `ibm-plex-sans-latin` plus the two Plex
    Mono latin weights;
  - the lending list with all seven guests loads the latin, latin-ext, vietnamese, greek and
    cyrillic subsets, and renders every glyph of the Polish, Vietnamese, Greek, Russian and
    Turkish/Czech names in Plex Sans;
  - Arabic falls back to DejaVu Sans and Chinese to Droid Sans Fallback (decision 3);
  - the printed lending slip (PDF) renders "Żółkiewski, Łukasz" in Plex Sans from the theme's
    font files.
- **Batch 2, redesigned within the batch** (decision 5): `card-flush` became `card-filled`
  before the batch was committed.
- **Batch 2, spacing:**
  - The panels keep the `mb-3` / `my-4` from the markup; there are no margin rules of their own.
  - Without a header rule, the body starts `.25rem` below the header.
- **Batch 2, `.card-caret`** skips its rotation transition under `prefers-reduced-motion`.
- **Batch 2, sticky offset fixed.** The old `.device-sidebar` rule used `top: 1rem`, which hid
  the aside's first section under the 57px sticky navbar on scrolling. It is `4.5rem` now.
- **Batch 2, template diffs.** The `device-sidebar` wrapper div is gone, and the record page's
  side column got the aside wrapper. Both re-indent their blocks, so `git diff -w` shows the
  real change: class swaps plus the wrapper.
- **Batch 2, the device add page** (`devices/form.html`) gets filled sections too, through the
  shared `_form_fields.html`.
- **Between batches 2 and 3:** persons, rooms, master data and tenants are already on
  `_detail_base`, but keep their outlined cards until batch 3.
- **Batch 2, checked in Chromium (2026-10-15)** on a scratch DB, light and dark, 1400px and
  390px:
  - device edit, with all sections open (the picked contact person keeps its card);
  - device read-only (user with `view_device` only);
  - a lent device (borrower link in *Current state*);
  - field history;
  - record detail;
  - the sticky aside after scrolling;
  - lending in picker mode, edit and return (also at 390px);
  - the hover on a collapsed bar, and a toggled collapse;
  - an empty start date, which shows the warning box around the field.
- **Batch 3, no `.detail-aside` wrapper on the journal and import detail pages.** The plan asked
  for one, but the aside has had no style since batch 2's redesign. The wrapper would only
  re-indent their side columns.
- **Batch 3, `licenses/history.html` included:** it is the twin of the device field history,
  which got the modifier in batch 2.
- **Batch 3, secondary header content.** The header's title style made the room page's change
  count and the person page's "Manage" link bold and 1.125rem. They are body text again.
- **Batch 3, checked in Chromium (2026-10-15)** on a scratch DB, at 1400px, plus light and dark
  and 390px where noted:
  - person: light, dark and 390px;
  - room, with the QR code open;
  - device type, manufacturer, tenant;
  - journal entry and journal cleanup;
  - import detail;
  - licence history.

  Timelines pick up the panel colour by themselves: `_timeline.scss` falls back to
  `--bs-card-bg`.
- **Batch 4, context:** `tiles` became `attention_tiles` and `stock_tiles`.
  - `_tile()` gives every tile the same keys: `value`, `unit`, `caption`, `tone`, `progress`,
    `level_counts`, `show_notes` and `note_count`.
  - `count` became `value`, and `show_badge` became `show_notes`.
  - The tests in `dashboard/tests/test_tiles.py`, `test_search.py` and
    `tenants/tests/test_multi_tenant.py` follow.
- **Batch 4, the inventory tile** is labelled with the inventory itself ("Inventory 2026"). It
  shows the done percentage with a bar, and "N of M devices" as its caption.
- **Batch 4, chart colours, checked with the dataviz validator** on both panel colours
  (`#f8f9fa` and `#2b3035`):
  - The states keep their badge colours. Lent takes Bootstrap's `$yellow-600` (`#cc9a06`)
    instead of `$yellow`, which failed the lightness band and reached only 1.55:1 on the light
    panel.
  - Lightness band, colour-blind and normal-vision separation pass.
  - Some marks stay under 3:1, so values sit at the bar ends, and the lines carry a legend and
    end labels.
  - "Removed" stays grey, the de-emphasised state, as on its badge.
- **Batch 4, chart form:**
  - Bars are 22px thick in a 36px slot, and each chart is as tall as its bars need.
  - Lines are 2px; only "in room", the bulk of the stock, gets a 10% wash.
  - Gridlines are hairlines that read on both panels.
  - The history chart has a unified hover over x.
- **Batch 4, the device type ranking** (`stats.device_type_ranking`):
  - A pure data function returning `(rows, total)`, from one query on `DeviceType` with a
    conditional `Count`.
  - The negated REMOVED condition keeps devices without any record.
  - The row bar is a `linear-gradient` on a per-row `--share` custom property, in the tint of
    the section icon squares (10% primary, 25% in dark mode). It needs no Plotly overrides and
    doubles as the table view the dataviz method asks for.
- **Batch 4, chart text in dark mode:** `_dashboard.scss` overrides Plotly's inline `fill` for
  tick labels, axis titles, legend, annotations and bar text with `--bs-secondary-color`. Hover
  labels keep Plotly's colours, since they bring their own background.
- **Batch 4, search result groups:**
  - The header shows its title as `<h2>` after the icon, so it gets the icon square.
  - `_cards.scss` leaves badges out of the secondary-text rule
    (`:where(a, span, small):not(.badge)`), so the count badge keeps its size.
- **Batch 4, checked in Chromium (2026-10-15)** on a scratch DB with backdated records, light and
  dark, 1400px and 390px:
  - tiles, with the overdue tone and the inventory progress;
  - the two charts and the ranking with 23 types: cut at 15, "All 23 device types", removed
    and soft-deleted devices not counted, hover, the rows' links;
  - a search for "NTB" with two result groups.
- **Batch 5, the journal entry page included:** its *Entry* list sits in the side column too, so
  it became a fact list. The plan had missed it.
- **Batch 5, checked in Chromium (2026-10-15)** on a scratch DB:
  - person with HR API data, tenant, room with UUID, device, record, journal entry, import detail;
  - the lending return flow, for the main-column list;
  - light and dark, 1400px and 390px.
- **Batch 6, the file name everywhere on the import pages:** besides the title and the list link,
  the *File* link on the detail page and the dry-run summary on the preview page show
  `file_name` too. The admin and the journal keep `str()`, the stored path.
- **Batch 6, checked in Chromium (2026-10-15):** lending in picker mode (also at 390px and in
  dark mode), edit and return; import detail with and without a file; the import list.
