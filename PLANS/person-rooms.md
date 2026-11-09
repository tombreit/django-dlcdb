<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Person rooms: a person's room from the HR API

**Status:** done (2026-11-09), batches 0–5. This is a living document:
each batch ticks its box in *Progress* in the same commit.

## Why

A new lending should start in the borrower's room. DLCDB has no link between a person and a room:
`Person` (`core/models/person.py`) has no room, and persons and rooms meet only through `Record`.

The room comes from the HR API that the HR sync already reads (`dataexchange/udb_sync.py`). Its
contracts carry `resources`. The workplace resource names a *workplace in a room*, not a room:

```json
"resources": [
  {
    "resource_type": {"name": "Arbeitsplatz", "name_en": "Workplace", "slug_id": "arbeitsplatz"},
    "resource": "Gü-235-02",
    "resource_info": [
      {"key": "Mapongo-URL", "value": "https://mpicsl.mapongo.de/viewer?l=1977&p=1", "...": "..."}
    ]
  }
]
```

`Gü-235-02` is workplace 02 in room 235 of the building `Gü`; the DLCDB room is `G235`. Other
institutes on the same HR API name their rooms differently.

The DLCDB rooms are a problem of their own: they are numbered without the building (`235`, not
`G235`), on the development and the production instance alike. They are renamed once, before the
HR sync can match them.

## Decisions taken

1. **One room per person:** `Person.room`, a nullable FK to `core.Room` (`SET_NULL`,
   `related_name="persons"`). A room has 0..n persons. No `limit_choices_to` (dropped in
   `core/0081`, review fix): forms offer active rooms through `Room.objects` anyway, and a room
   deactivated later must stay valid for its person, which model validation would refuse. Lending needs exactly one room per person, and a plain FK is native
   Django.
2. **Only the room is stored:** the room as HR names it (`Gü-235-02`) only yields the DLCDB room;
   the person does not keep it. The run log names the HR value of a room it cannot find.
3. **A room number rule maps the HR value, configured:** a regex pattern and a replacement on the
   existing `UdbSyncConfiguration` (`room_number_pattern`, `room_number_replacement`), applied with
   `re.sub`. The rule and its names are general; that CSL's HR value is a workplace in a room is
   CSL's data, not the mechanism (wording decided 2026-11-09).
   - CSL: `^(\w)\w*-(\d+[a-z]?)(?:-\d+)?$` → `\1\2`. The first idea, `^(\w)\w*-(\d+)-\d+$`,
     missed HR values without a workplace number (`Gü-324`, 15 at CSL) and with a letter
     (`Gü-223a-01`, 2): 140 of 160 matched a room in the dev data, the broader rule 155.
   - An empty pattern takes the HR value as the room number.
   - No code is needed per institute.
4. **Room-plan URL:** the first `resource_info[].value` of the room resource that passes
   `URLValidator`. It is not keyed on `Mapongo-URL`, which is CSL's key. HR overwrites
   `Room.website` ("e.g. a URL to a room plan"), so a changed link propagates.
5. **Unknown room number:** the person gets no room, and the contract's row in the run log notes
   it ("HR room Gü-235-02 → G235: no such room in DLCDB"). No extra SKIPPED row (review fix): one
   row per contract, the run is no warning and is not journaled; the non-verbose log lists an
   UNCHANGED row when it carries such a note. The sync creates no rooms; the room list is
   curated by hand. A soft-deleted room counts as unknown.
6. **Code-owned, like the existing request filters and fields:**
   - the resource type that names a person's room, `UDB_ROOM_RESOURCE_TYPE = "arbeitsplatz"`
     (at CSL a workplace in a room);
   - `resources` in `UDB_SYNC_CONTRACT_FIELDS`.

   Either one becomes a config field when another institute needs a different value.
7. **Who owns the room:**
   - HR-synced persons are read-only in the frontend (`persons/views.py`), so HR owns their room.
     A person without a room in HR has no room.
   - Persons without an HR link (guests) get a `room` field in `PersonForm`.
8. **Rooms are renamed in the rooms frontend:** a batch rename with the same `re.sub` syntax
   (`^(\d+)$` → `G\1`), a preview first, then apply. Details:
   - only active rooms are renamed;
   - collisions are checked against all rooms, soft-deleted ones included, because `Room.number` is
     unique in the database;
   - a colliding rename is skipped and listed, never merged;
   - one journal entry (`rooms.rename`) lists every rename.
9. **No shared regex helper:** two four-line `try/except` blocks (the rename form and
   `UdbSyncConfiguration.clean()`) read better than a helper in `core`.
   `re.sub(pattern, replacement, "")` raises on a bad pattern and on a bad group reference, even
   without a match.

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| The institute's staff list JSON (`slug`, `email`, `room`) as source, with its own importer | The HR API already carries the workplace; one source, one sync, one matching logic. |
| A Python adapter selected by a setting (`DLCDB_WORKPLACE_TO_ROOM = "dotted.path"`) | Every other institute would have to deploy code. A regex covers the naming schemes seen so far; the setting can be added when one does not fit. |
| A hard-coded CSL helper | Not usable by other institutes on the same HR API. |
| The sync creates unknown rooms (`dataexchange/fields.py:create_fk_obj`) | HR would decide which rooms exist; typos and values like "Homeoffice" would become rooms. |
| A separate `PersonRoom` model or an M2M | Lending needs one room per person; HR names one room per contract. |
| Keeping the raw workplace (`Person.udb_contract_workplace`) | Nothing uses it: lending needs the room, and the run log names the workplace of an unknown room (decided 2026-11-09). |
| A website entered by hand wins over HR | HR link changes would never arrive. |

## Plan

### Batch 1 – Batch rename of rooms

- **`rooms/rename.py`:**
  - `plan_renames(pattern, replacement)` returns one `Rename(room, old, new, problem)` per active
    room whose number `re.sub` changes. `problem` is set when the new number:
    - is empty;
    - is longer than `Room.number`'s `max_length`;
    - is held by another room in any spelling the add page counts as the same
      (`theme.similar.comparable_name`: "g-235" is "G235"), soft-deleted ones included, even when
      that room is renamed away in the same batch (no swaps or chains);
    - is the target of two renames.
  - `apply_renames(pattern, replacement, *, user)` recomputes the plan and renames the rows without
    a problem in one transaction (`stamp_user`, `save`). It writes one journal entry and returns
    the renames.
- **Form, view and URL:** `RoomRenameForm`, the view `room_rename`
  (`@htmx_permission_required("core.change_room")`) and `rooms:rename`.
  - GET with `?pattern=&replacement=` renders the preview.
  - POST applies it and returns to the list, or to the preview when rooms kept their number:
    the preview then lists them with the reason.
- **Templates:** `rooms/rename.html`, and a "Rename rooms" button on the rooms list.
- **Tests:**
  - no matches: nothing to rename;
  - the CSL case;
  - each problem kind is skipped;
  - apply renames and journals;
  - a bad pattern or group reference is a form error;
  - 403 without `core.change_room`.
- **Docs:** `docs/guides/erste_schritte.md` §6, Räume; a `NEWS.md` line.

### Batch 2 – Person ↔ room

- **Model:** `Person.room`, migration `core/0080_person_room`.
- **Person form:** `PersonForm` gets `room` (`TomSelectWidget`), with the open/add buttons of
  `theme.related` on the add and detail pages.
- **Person detail:** shows the room linked to its page.
- **Person list:** a sortable *Room* column (`select_related`, no extra query).
- **Room detail:** a *Persons* card in the sidebar listing the persons in the room (with
  `core.view_person`).
- **Room list:** a sortable *Persons* column next to *Assets*, counted in a correlated subquery
  (a join next to the records would repeat every record row per person).
- **Docs:** `docs/betrieb/model.md`, the ER diagram and *Person*.
- **Tests:**
  - a manual person saves a room; a deactivated room is refused;
  - the room select adds a room and comes back with it;
  - the person detail shows the room; the person list shows it and sorts by it;
  - the room detail lists its persons, not deactivated ones, only with `core.view_person`;
  - the room list counts persons without changing the assets count, and sorts by them.

### Batch 3 – Room number rule in the HR sync configuration

- **Config fields:** `UdbSyncConfiguration.room_number_pattern` and `room_number_replacement`, with
  a migration `dataexchange/0012_udbsyncconfiguration_room_number_rule`. `clean()` validates the pair
  and refuses a replacement without a pattern.
- **Rule function:** `udb_sync.map_room_number(hr_room, config)` is a pure function.
- **Tests:**
  - `Gü-235-02` → `G235`;
  - an empty pattern returns the value verbatim;
  - a non-matching value comes back unchanged;
  - `clean()` rejects a bad pattern, a bad group reference and a replacement without a pattern.

### Batch 4 – The HR sync assigns rooms

- **Request:** `resources` in `UDB_SYNC_CONTRACT_FIELDS`, and the constant
  `UDB_ROOM_RESOURCE_TYPE`.
- **Parsing:** `_hr_room(contract)` returns `(hr_room, plan_url)`; `_resolve_room(contract, config)`
  maps it with `map_room_number` and looks the room up (`number__iexact`, active rooms only). It
  returns `(room, plan_url, problem)`, inside the contract's savepoint.
- **The loop** passes `room` and `plan_url` to `_process_contract` and records a problem as an extra
  SKIPPED row for the same contract: "HR room Gü-999-01 → G999: no such room in DLCDB".
- **`_process_contract`:**
  - sets `room` (None when HR names none or DLCDB lacks it);
  - `_sync_room_website` overwrites `Room.website`, stamped by the sync user, with an admin
    `LogEntry`; the change makes the row UPDATED and is always in its detail.
- **Change detection:** `COMPARED_PERSON_FIELDS` gains `room`.
- **Tests:** `_contract(…, room=…, plan_url=…)`, covering:
  - the room is mapped by the rule; without a rule the HR value is used, case-insensitively;
  - an unknown or deactivated room is SKIPPED and the run a warning;
  - no room in HR clears the room;
  - other resource types and `resource_info` values that are no URL are ignored;
  - the website is overwritten (history entry, sync user), then UNCHANGED on the next run;
  - the request asks for `resources`.
- **Docs:** `docs/betrieb/hr-sync.md`, section *Raum*.
- **NEWS:** the batch 2 line in `NEWS.md` is extended, not a second line.

### Batch 5 – A new lending starts in the borrower's room

The person is picked in the browser in both modes of the lend page, so the default is set there.
A server-side initial cannot know the person on GET. The simplest rule, chosen over a version that
tracked a room chosen by hand:
- **Person:** picking a person with a room sets the room to it; a person without one leaves it.
- **Device (picker mode):** picking a device sets its room unless the picked person has one, so the
  order of picking does not matter.

Changes:
- `_person_list_item.html` carries `data-room-id` (no query).
- In `lend.html`, the inline script runs for the lend flow of both modes: `setRoom()` (sets nothing
  for a room the select does not offer, as TomSelect would clear it) and a `picker:selected`
  listener on `#person-picker`. The device listener uses the selected person card's room first.
- The help text names the rule. A test covers `data-room-id` on the person search results; the
  behaviour was checked in the browser.

## Rollout on an instance

1. Rename the rooms (`^(\d+)$` → `G\1` at CSL, then `^(\d+[a-zA-Z])$` → `G\1` for rooms with a
   letter); check the preview first.
2. Set the room number rule in *Settings › HR API sync configuration*
   (`^(\w)\w*-(\d+[a-z]?)(?:-\d+)?$` → `\1\2` at CSL).
3. Watch the next HR sync runs for SKIPPED rooms; create or rename those rooms.

## Pitfalls

- **An empty rule matches nothing at CSL:** the HR value is then taken verbatim, and every contract
  naming a room is SKIPPED (dev instance, 2026-11-09: `246 unchanged, 160 skipped`).
- **A deactivated room blocks a rename in another spelling:** at CSL, a deactivated `G 141` kept
  the active `141` from becoming `G141`. Give the deactivated room another number in the admin
  first.
- **Device CSV imports use room numbers:** a CSV that still says `235` creates a new room `235`
  after the rename (`dataexchange/fields.py:create_fk_obj`).
- **Room reconcile prefixes:** the room reconcile maps Archibus buildings to number prefixes
  (`rooms/views.py`, `ARCHIBUS_BUILDING_ROOM_PREFIXES = {"STRA-SFU": "F"}`). After the rename, the
  main building's Archibus `bl_id` needs `"G"` there.
- **`re.sub` errors:** an invalid group reference raises `re.error`, an unknown named group
  `IndexError`; validation catches both.
- **Several contracts per person:** the last processed one wins, as for every other contract
  field.
- **Website flip-flop:** two workplaces in the same room with different plan URLs would flip
  `Room.website` on every run (UPDATED each time).

## Review fixes (2026-11-10)

A code review of the whole branch found 10 issues; 8 were fixed in one commit:
- **Rename:** confirming returns to the room list and names the rooms that kept their number in a
  message. The preview after a partial rename used to re-plan the renamed rooms (a pattern
  matching its own output offered `G235 → GG235`). Only rooms the pattern matches are planned.
- **HR sync:**
  - rooms are matched like on the add page (`comparable_name`, read once per run, no query per
    contract);
  - the website is saved with `update_fields`, and a plan URL over 200 characters is ignored;
  - a missing room is a note on the contract's row (decision 5).
- **Lending:** a person without a room falls back to the device's room.
- **Deactivated room on a person:**
  - the person form also offers the person's own deactivated room, so saving keeps it;
  - the person pages show it without a link (decision 1).
- **Room list:**
  - the *Persons* column and its sort option need `core.view_person`;
  - the list is ordered explicitly, so a refused sort no longer leaves it unordered (the
    paginator warned).

Not fixed: the website flipping between workplaces of one room with different plan URLs; at CSL
the plan URL belongs to the room.

## Progress

- [x] **0. This document**
- [x] **1. Batch rename of rooms**
- [x] **2. Person ↔ room**
- [x] **3. Room number rule in the HR sync configuration**
- [x] **4. The HR sync assigns rooms**
- [x] **5. A new lending starts in the borrower's room**
