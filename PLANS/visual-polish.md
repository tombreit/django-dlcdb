<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Visual polish: typeface, lighter detail pages, dashboard

**Status:** all batches implemented 2026-10-15:
- batch 1, the typeface;
- batch 2, `card-filled` sections on the device, record and lending pages;
- batch 3, the other detail pages;
- batch 4, the dashboard.

What is left is under *Open follow-ups*. This is a living document.

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

     ▤ Devices by state               ▤ Devices by type
     ──────────────────────           ──────────────────────
     …                                …
     ▤ Device history
     ──────────────────────

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
   - The different column ratios (`col-sm-3/9`, `4/8`, `5/7`, `6/6`) are an open follow-up.
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
10. **NEWS:** no entry per batch. At the end, one line is offered in the summary: this is polish
    (AGENTS.md).

## Progress

After each batch, stop so the user can commit it.

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

## Open follow-ups

- **Primary colour:** indigo is kept for now. It is Tailwind's default, so it reads as generic.
- **Plex Sans for other scripts:** self-host Plex Sans Arabic, Hebrew and so on if names in those
  scripts become common.
- **Read-only `dl` column ratios:** unify them.
- **Lending page polish:**
  - align its header with `_detail_base` (back link right, `h1.h3`);
  - drop the inline `.picker-option:hover` style, which duplicates `picker.css`.
- **Plain cards left on non-detail pages:**
  - the subscription form on `notifications/index.html`;
  - the info card on `dataexchange/import.html`.

  One `card-filled` each, if wanted.
- **Page headers:** the import detail page's title is a small grey "Import" line, unlike the
  other detail pages.
- **Out of scope for this round:** list pages (`_index_base.html`), the filterbar, and one page
  header for index, detail and lending pages.
- **New msgids to translate (batch 4):**
  - "Needs attention" and "Stock";
  - "of %(total)s lendable" and "%(done)s of %(total)s devices";
  - "Devices by state";
  - "No device type has %(count)s or more devices yet."

  The chart's state labels reuse the lifecycle labels, and the notes caption reuses the old
  badge's msgid.
- **`Device` verbose names are untranslated:** the Devices tile reads "Devices" in the German UI.
  This predates this work.
- **Charts have no table view:** the dataviz method asks for one per chart. Values are reachable
  through the labels, the hover tooltips and the linked lists.
- **Device detail:** the state badge shows twice, in the header and under *Current state*.
- **Identifiers set in Plex Sans:** Plex Sans's zero has no inner mark, so `0`/`O` and `1`/`I`/`l`
  look alike there. Plex Mono's zero has one. These identifiers are still in Sans:
  - serial number and ID form inputs;
  - the device line of the lending slip.

  `.font-monospace` on them would need template changes.
- **Lending slip checklist:** `lending/includes/lent_checklist.html` sets `font-family: monospace`
  inline, which uses the system monospace font, not Plex Mono.
- **Icons:**
  - devices use `bi-upc` on the tiles but `bi-pc-display` in the navbar;
  - Lost reuses Records' `bi-stack`.
- **The admin keeps Roboto.** The admin is being phased out.

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
  - Devices by type is one series in one colour, `#6366f1`, one indigo step lighter than the
    primary: 4.2:1 light, 3.0:1 dark.
- **Batch 4, chart form:**
  - Bars are 22px thick in a 36px slot, and each chart is as tall as its bars need.
  - Lines are 2px; only "in room", the bulk of the stock, gets a 10% wash.
  - Gridlines are hairlines that read on both panels.
  - The history chart has a unified hover over x.
  - The device type chart shows a note instead of an empty plot when no type reaches
    `DEVICE_TYPE_MIN_COUNT` (10, formerly a bare literal).
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
  - the three charts;
  - a search for "NTB" with two result groups.
