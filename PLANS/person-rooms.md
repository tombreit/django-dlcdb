<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Person rooms: a person's room from the HR API

**Status:** planned (2026-11-09). Batch 0 (this document) is done. This is a living document:
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
institutes on the same HR API name their workplaces differently.

The DLCDB rooms are a problem of their own: they are numbered without the building (`235`, not
`G235`), on the development and the production instance alike. They are renamed once, before the
HR sync can match them.

## Decisions taken

1. **One room per person:** `Person.room`, a nullable FK to `core.Room` (`SET_NULL`,
   `related_name="persons"`, `limit_choices_to={"deleted_at__isnull": True}` like `Record.room`).
   A room has 0..n persons. Lending needs exactly one room per person, and a plain FK is native
   Django.
2. **The raw HR value is kept:** `Person.udb_contract_workplace` (`Gü-235-02`), next to the other
   `udb_contract_*` mirror fields. It shows what HR says when no room matches.
3. **The workplace → room rule is configuration:** a regex pattern and a replacement on the
   existing `UdbSyncConfiguration`, applied with `re.sub`.
   - CSL: `^(\w)\w*-(\d+)-\d+$` → `\1\2`.
   - An empty pattern takes the workplace as the room number.
   - No code is needed per institute.
4. **Room-plan URL:** the first `resource_info[].value` of the workplace resource that passes
   `URLValidator`. It is not keyed on `Mapongo-URL`, which is CSL's key. HR overwrites
   `Room.website` ("e.g. a URL to a room plan"), so a changed link propagates.
5. **Unknown room number:** the person gets no room, and the run log gets a SKIPPED row
   ("workplace Gü-235-02 → room G235 not in DLCDB"). The sync creates no rooms; the room list is
   curated by hand. A soft-deleted room counts as unknown.
6. **Code-owned, like the existing request filters and fields:**
   - the workplace resource type `UDB_WORKPLACE_RESOURCE_TYPE = "arbeitsplatz"`;
   - `resources` in `UDB_SYNC_CONTRACT_FIELDS`.

   Either one becomes a config field when another institute needs a different value.
7. **Who owns the room:**
   - HR-synced persons are read-only in the frontend (`persons/views.py`), so HR owns their room.
     A person without a workplace in HR has no room.
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
| A separate `PersonRoom` model or an M2M | Lending needs one room per person; the HR workplace is one value per contract. |
| A website entered by hand wins over HR | HR link changes would never arrive. |

## Plan

### Batch 1 – Batch rename of rooms

- **`rooms/rename.py`:**
  - `plan_renames(pattern, replacement)` returns one `Rename(room, old, new, problem)` per active
    room whose number `re.sub` changes. `problem` is set when the new number:
    - is empty;
    - is longer than `Room.number`'s `max_length`;
    - is held by another room, case-insensitively, soft-deleted ones included, unless that room is
      renamed away in the same batch;
    - is the target of two renames.
  - `apply_renames(pattern, replacement, *, user)` recomputes the plan and renames the rows without
    a problem in one transaction (`stamp_user`, `save`). It writes one journal entry and returns
    the renames.
- **Form, view and URL:** `RoomRenameForm`, the view `room_rename`
  (`@htmx_permission_required("core.change_room")`) and `rooms:rename`.
  - GET with `?pattern=&replacement=` renders the preview.
  - POST applies it and returns to the list.
- **Templates:** `rooms/rename.html`, and a "Batch rename" button on the rooms list.
- **Tests:**
  - no matches: nothing to rename;
  - the CSL case;
  - each problem kind is skipped;
  - apply renames and journals;
  - a bad pattern or group reference is a form error;
  - 403 without `core.change_room`.
- **Docs:** `docs/guides/erste_schritte.md` §6, Räume.

### Batch 2 – Person ↔ room

- **Model:** `Person.room` and `Person.udb_contract_workplace`, with a core migration.
- **Person form:** `PersonForm` gets `room` (`TomSelectWidget`).
- **Person detail:** shows the room linked to its page, and, for HR persons, the workplace.
- **Room detail:** a *Persons* card listing the persons in the room.
- **Docs:** `docs/betrieb/model.md`, the ER diagram and *Person*.
- **Tests:**
  - a manual person saves a room;
  - the person detail shows the room and the workplace;
  - the room detail lists its persons.

### Batch 3 – Workplace rule in the HR sync configuration

- **Config fields:** `UdbSyncConfiguration.workplace_pattern` and `room_number_replacement`, with a
  dataexchange migration. `clean()` validates the pair.
- **Rule function:** `udb_sync.workplace_room_number(workplace, config)` is a pure function.
- **Tests:**
  - `Gü-235-02` → `G235`;
  - an empty pattern returns the value verbatim;
  - a non-matching value comes back unchanged;
  - `clean()` rejects a bad pattern and a bad group reference.

### Batch 4 – The HR sync assigns rooms

- **Request:** `resources` in `UDB_SYNC_CONTRACT_FIELDS`, and the constant
  `UDB_WORKPLACE_RESOURCE_TYPE`.
- **Parsing:** `_workplace(contract)` returns `(workplace, plan_url)`.
- **`_process_contract`:**
  - sets `udb_contract_workplace` and `room`;
  - overwrites `Room.website` with an admin `LogEntry`;
  - returns the unknown-room problem, which the loop records as an extra SKIPPED row.
- **Change detection:** `COMPARED_PERSON_FIELDS` gains `room` and `udb_contract_workplace`.
- **Tests:** `_contract(…, workplace=…, plan_url=…)`, covering:
  - the room is mapped;
  - an unknown room is SKIPPED;
  - no workplace means no room;
  - the website is overwritten, then UNCHANGED on the next run;
  - the request URL asks for `resources`.
- **Docs:** `docs/betrieb/hr-sync.md`, section *Raum und Arbeitsplatz*.
- **NEWS:** `NEWS.md`.

### Later – Lending starts in the borrower's room

Planned when batches 1–4 have landed:
- `LendingForm` and `lend.html` preset the room from `person.room`.
- **Record mode:** server-side initial.
- **Picker mode:** `data-room-id` on `_person_list_item.html` plus a `picker:selected` listener on
  `#person-picker`. It fills the room only when it is empty, like `maybeFillDate`, and must settle
  its precedence against the device-room prefill in `lend.html`.

## Rollout on an instance

1. Rename the rooms (`^(\d+)$` → `G\1` at CSL); check the preview first.
2. Set the workplace rule in *Settings › HR API sync configuration*.
3. Watch the next HR sync runs for SKIPPED rooms; create or rename those rooms.

## Pitfalls

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
- **Unknown rooms are journaled:** an unknown room is reported with every run (every 10 minutes);
  `journal/cleanup.py` already collapses repeated HR sync entries.

## Progress

- [x] **0. This document**
- [ ] **1. Batch rename of rooms**
- [ ] **2. Person ↔ room**
- [ ] **3. Workplace rule in the HR sync configuration**
- [ ] **4. The HR sync assigns rooms**
