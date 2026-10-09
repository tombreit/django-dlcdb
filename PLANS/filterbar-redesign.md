<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Filterbar redesign: one rail

**Status:** implemented (batches 0–3, 2026-10-09), after `PLANS/filterbar.md` (tenant
filter, backend cleanup, "Clear filters" button). This document covers only the look and
feel of the bar and the status line; what is left is under *Ideas, not now*.

## Context

The bar (`theme/templates/theme/filterbar/filterbar.html`, `_dropdown.html`,
`chips.html`, `assets/scss/_filterbar.scss`, `assets/js/filterbar.js`) works and is used
by eleven list pages. What it looks like today, at desktop width:

```
[⌕ | Search devices…        ]  [Type ▾] [State ▾] [Loanable ▾] [Room ▾] [Manufacturer ▾] [⇅ Sort ▾]
                                                                                    ˅ More filters
3 of 120 devices  (State: Lent ×) (Room: 101 ×) Clear all          ⤓ Export 3 devices as CSV
```

Why it reads as cluttered and heavy, from the markup:

- **Two tones.** The search input has the hairline form border (`--bs-border-color`,
  light grey), the buttons are `btn-outline-secondary` (mid-grey border and text). Same
  row, two weights: that is the "not from one mold" effect.
- **Default size.** Every control is 38 px tall (`form-control`, `btn`); each dropdown is
  its own bordered box with its own gap. Six boxes in a row look like a toolbar.
- **The search icon sits in a grey `input-group-text` box**, a third tone.
- **"More filters" floats** below, right-aligned, as a small link unrelated to the rail.
- **The status line is written three ways** (`includes/_list_status.html`,
  `lending/index.html`, `dataexchange/importer_index.html`).

What stays: the data shape from `theme/filterbar.py` (no Python change), the HTMX
contract (form-level `hx-get`, fragment swap, chips inside the fragment), the delegated JS,
the offcanvas on small screens, the dropdown menus with radios/checkboxes and the in-menu
option filter.

## Design

**One rail.** The search field and the filters become two pieces of the same strip:
same height, same hairline, same text colour, joined buttons. The sort is the last
segment; "More" is a segment too. Nothing new is invented: Bootstrap's `input-group-sm`
and `btn-group-sm` (nested `btn-group` for dropdowns, as documented) do the joining.

```
Desktop (≥ md)
Devices                                                             [+ Add device] [Import ▾]

┌─────────────────────────────┐ ┌──────┬───────┬──────────┬──────┬──────────────┬────────┬──────────┐
│ ⌕  Search devices…          │ │ Type ▾ State ▾ Loanable ▾ Room ▾ Manufacturer ▾ ⋯ More │ ⇅ Sort ▾ │
└─────────────────────────────┘ └──────┴───────┴──────────┴──────┴──────────────┴────────┴──────────┘
                                ┌──────────┬───────────┬────────┬─────────────┬────────────┐
   (collapse, when More is open)│ Supplier ▾ Inventory ▾ Import ▾ Import file ▾ Duplicates ▾│
                                └──────────┴───────────┴────────┴─────────────┴────────────┘
3 of 120 devices  (State: Lent ×) (Room: 101 ×)  [× Clear filters]           ⤓ Export 3 devices as CSV

Small (< md)
┌──────────────────────────┬─────────────┐
│ ⌕  Search devices…       │ ⚲ Filters 2 │      → offcanvas: the same group, stacked
└──────────────────────────┴─────────────┘
```

Tokens: none new. Height from `-sm` (31 px). Border `var(--bs-border-color)`, text
`var(--bs-body-color)`, hover `var(--bs-tertiary-bg)`, selected menu item bold as today.
Dark mode follows, since only `--bs-*` variables are used.

Active state: a filter with a value shows "Type: Laptop" (as today, JS + server) and is set
in `font-weight: 600` by CSS (`:has(input:checked:not([value=""]))`), no JS change. The
sort shows "Sort: Modified ↓". "More" is bold while a secondary filter is active
(`bar.secondary_active`).

## Decisions taken

1. **Sizes:** `input-group input-group-sm` for the search, `btn-sm` on every button of
   the rail and on the mobile toggle. Not `btn-group-sm`: it sizes only direct children,
   and the dropdown buttons sit in nested groups (found in batch 1, the nested buttons
   stayed 38 px and stretched the rail). No `-lg` anywhere, no custom heights.
2. **One tone, one class:** `filterbar-btn` on every button of the bar (and on the "Clear
   filters" button from `PLANS/filterbar.md` batch 3). It sets Bootstrap's button CSS
   variables (`--bs-btn-color`, `--bs-btn-bg`, `--bs-btn-border-color`, hover/active
   variants) to the form-control tokens. About ten lines of SCSS, no new colours.
3. **Search icon inside the field:** the `input-group-text` loses its background and its
   right border (three lines of SCSS). The input keeps `type="search"` (native clear ×)
   and gets an `aria-label` (today it has only a placeholder).
4. **Each filter is a nested `btn-group`** (`<div class="btn-group filterbar-filter">`)
   instead of a `dropdown` div. Bootstrap joins nested groups; the dropdown JS is the same.
   `filterbar-filter`, `filterbar-sort`, `data-filterbar-*` hooks are unchanged, so
   `filterbar.js` is untouched.
5. **"More" is a segment of the group**, label stays `More filters` (existing msgid, tests
   assert on it), icon `bi-sliders`; it keeps `data-bs-toggle="collapse"`. The secondary
   row is a second `btn-group btn-group-sm` in the collapse, left-aligned under the group
   with `mt-2`.
6. **Sort is the last segment.** Label and icon as today.
7. **One status line.** `includes/_list_status.html` is the only status line. Lending's
   "(N available, M lent)" goes into its `count_label`; its export link keeps the shared
   "Export N devices as CSV", which is the right noun there (the count counts devices,
   and the old template said so in a comment). The `export_label` parameter planned here
   was therefore not needed (batch 2). `importer_index.html` extends `_index_base.html`
   like every other list.
8. **Mobile:** inside the offcanvas the group stacks: `flex-direction: column`, each
   button full width, left-aligned text, normal radius (about ten lines of SCSS replacing
   the current mobile block).
9. **No in-bar reset.** The reset lives in the status line (batch 3 of
   `PLANS/filterbar.md`); a reset inside the bar needs JS to show/hide it. Not now.
10. **No Python change** in `theme/filterbar.py`.

## Batches

### 0 — This document and baseline screenshots
- `/verify`: screenshots of devices (with "More filters"), lending, imports; desktop and
  375 px; light and dark. Saved under the scratchpad, compared after batch 1 and 3.

### 1 — One rail
- `filterbar.html`:
  - search: `input-group input-group-sm filterbar-search`, `aria-label`;
  - wrapper after the search: `<div class="btn-group btn-group-sm" role="group">`
    containing the primary `_dropdown.html` includes, the More toggle, the sort group;
  - mobile toggle `btn btn-sm filterbar-btn d-md-none`;
  - secondary: `collapse` with a second `btn-group btn-group-sm`.
- `_dropdown.html`: `<div class="btn-group filterbar-filter">`, button
  `btn filterbar-btn dropdown-toggle`.
- `_filterbar.scss`: `.filterbar-btn` variables; `.filterbar-search .input-group-text`
  flat; active-filter `:has()` rule; mobile stacking; the rest as today.
- Tests: existing assertions hold (`data-filterbar-label` count, "More filters",
  `aria-expanded`, `collapse show`). Add none.
- `NEWS.md`, one line: "Search and filter bar: smaller, one strip of search, filters and
  sort".
- Commit: `Filterbar redesign, step 1: search, filters, More and sort form one small rail
  in one tone`

### 2 — One status line
- `lending/index.html:23-46` and `dataexchange/importer_index.html:7-28` use the include;
  importer index extends `_index_base.html`. No change to `_list_status.html`.
- Tests: none assert on the export label; the existing lending and importer tests cover
  the count line and the chips.
- No NEWS.
- Commit: `Filterbar redesign, step 2: lending and import history use the shared status
  line`

### 3 — Small screens
- Offcanvas body: stacked group, `Filters` header as today; screenshots at 375 px.
- Found in batch 3: the stacking rule from batch 1 stretched only the primary group, since
  a `btn-group` is `inline-flex` and the secondary group sits inside the collapse. One
  `display: flex` on the stacked groups fixes it. Checked at 375 px (panel closed, open,
  secondary row expanded, a menu open, a value picked) and at 820 px (rail wraps under
  the search).
- No NEWS.
- Commit: `Filterbar redesign, step 3: the filter panel on small screens stacks the same
  rail`

## Ideas, not now

- `/` focuses the search (one keydown listener).
- A count badge on "More" (needs `secondary_active` as a count in `filterbar.py`).
- Reset segment inside the rail (JS-controlled visibility).
- The dashboard global search (`dashboard/includes/_search_bar.html`, `form-control-lg`)
  and `smallstuff/person_search.html` (`input-group-lg`) could take the same
  `input-group-sm` + flat icon look.
- The sort dropdown offers fields that have no column (e.g. Tenant for single-tenant
  users); a follow-up in `PLANS/filterbar.md`.
- **Tenant column and sort** exist only on the device list. The record, lending, licence and
  import lists have none.
- **The device sort dropdown offers "Tenant" to single-tenant users**, while the column is hidden.
- **Lending runs a second COUNT:** the paginator counts on top of the state aggregate
  (`lending/views.py:138`).

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| GitLab-style single input with typed tokens (`state:lent`) | A parser, token rendering and keyboard handling: far more JS, and the dropdown menus already give discoverability. |
| GitHub-style ghost text filters (no borders) | Zero SCSS, but the filters then float next to a bordered input; it is lighter, not more integrated. Asked 2026-10-09, "one rail" chosen. Can be revisited if the rail still feels heavy. |
| Everything in one `input-group` (search and buttons in the same group) | The offcanvas wrapper sits between the group and the buttons, so Bootstrap's direct-child joining rules do not apply; it would need custom joining CSS. |
| Replacing `btn-outline-secondary` globally | Touches every page; the bar's tone is a local decision. |
| A `<select>`-based bar | Loses multi-select, option filter, and the chip/label sync. |

## Pitfalls

- The `redesign` branch (`theme-next.css`, `scss/next/_filterbar.scss`) is not on this
  branch; when it is rebased, its filterbar partial must restyle the new structure.
- `btn-group` adds `margin-left: -1px` to nested groups; inside the offcanvas this must be
  reset to 0 when stacking.
- The sort group has no empty radio; the `:has()` bold rule must not match it when nothing
  is picked (it does not: nothing is checked by default).
- `lending/tests/test_views.py:145-224` counts `data-filterbar-label` and asserts on
  checked radios; keep the attributes.

## Progress

- [x] 0 — This document, baseline screenshots
- [x] 1 — One rail
- [x] 2 — One status line
- [x] 3 — Small screens

## Verification (each batch)

- `npm run build` then `.venv/bin/pytest dlcdb/theme dlcdb/lending dlcdb/licenses
  dlcdb/assets dlcdb/dataexchange`, then `.venv/bin/pytest .`
- `/verify`: screenshots of devices, lending, imports at 1280 px and 375 px, light and
  dark; one filter picked, one search term, "More filters" open; compare with batch 0.
