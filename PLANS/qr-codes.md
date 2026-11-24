<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# QR codes: generated on request, not stored

**Status:** step 1 done (2026-11-24). This is a living document.

## Why

Devices and rooms get a QR code that encodes `QRCODE_PREFIX + infix + uuid`
(`DLCDBD3f2c…`). `Device.save()` and `Room.save()` render it with segno and
store the SVG in a `FileField` under `data/media/qrcode/`. The inventory
scanner (`qr_inventorize.js`) reads printed labels.

- **The files are a cache that is never invalidated, and it costs more than
  rendering.** The SVG depends only on the uuid, which never changes. Rendering
  takes 1.7 ms and gives about 1.5 KB. Serving a stored file runs
  `media_views._visible_in_tenants`, which filters
  `Device._base_manager.filter(qrcode=…)` on an unindexed column, up to twice
  per `<img>`. The room printout does that once for each device it lists.
- **Orphans pile up.** A development checkout held 209,454 files (835 MB): 48k
  room codes, 1,677 from before the infix. They come from:
  - importer dry-runs: `rollback_atomic()` rolls back the rows, but
    `Device.save()` has already written a file for a fresh random uuid;
    failed rows inside a savepoint do the same
  - hard deletes, which leave the file behind
  - test runs before e41d15f6
  - `/verify` runs, which isolate the database but not `MEDIA_ROOT`
- **The scanner ignores the settings.** It hardcodes `^DLCDB[RD]`, and its UUID
  regex accepts only versions 1–5 (no UUIDv7) and lowercase only.
- **A foreign QR code pops up an `alert()`.** The `QrCode` constructor does
  `return false`, which `new` ignores, so `if (!QrObj)` never fires.

## Decisions taken

- **The payload stays as it is:** prefix, infix and uuid. Printed labels keep
  working. The uuid is the identity because it is unique, not editable and
  never reused; `sap_id`/`edv_id` can change.
- **`QRCODE_PREFIX` and `QRCODE_INFIXES` stay settings, and the scanner reads
  both** from `js_vars`.
- **Labels without an infix (`DLCDB<uuid>`) are not supported.** None are in
  use.
- **A stateless view renders the code:**
  `GET /core/qrcode/<str:model_name>/<uuid:uuid>.svg`, where `model_name` is
  a key of `QRCODE_INFIXES` (`device`, `room`).
  - `model_name` is Django's term for this value: `Device._meta.model_name`
    is `"device"`, and the admin URL names use it too.
  - It makes no DB query and no tenant check. The image holds only what its
    URL holds, so it reveals nothing and confirms no object exists. The login
    still applies through `LoginRequiredMiddleware`.
  - `Cache-Control: private, max-age=31536000, immutable`, because the image
    never changes.
- **`segno.make_qr(…, error="m")`** instead of `segno.make()`. This rules out
  Micro QR, and a future segno default cannot change new labels.
- **Nothing outside DLCDB uses `/media/qrcode/` URLs**, so no compatibility
  route is needed.

## Alternatives rejected

- **A URL in the QR code** (`https://host/…/<uuid>`): any phone camera could
  open the page, but every printed label would depend on the hostname forever.
- **Inline SVG in the pages:** the HTML grows with every code, and the views
  would have to render each code, or we'd need a template tag. The view needs
  only a new `src`, and the browser caches the image.
- **An uppercase payload** (alphanumeric mode, 25×25 instead of 29×29): only
  worth it for tiny labels, and the scanner would have to accept both forms.
- **Other names for the URL's `model_name`:**
  - `obj`/`instance`: in Django these hold a model instance, but the segment
    names the model; the uuid picks the instance.
  - `kind`, `obj_type` (the inventory note URLs): not Django terms.
  - `content_type`: in Django this means a `ContentType` row, and the HTTP
    `Content-Type` sits right next to it in this view.
  - Two routes (`core:device-qrcode`, `core:room-qrcode`): every further model
    would need a route of its own.

## Pitfalls

- `core/storage.OverwriteStorage` must stay even when no field uses it any
  more. `core/migrations/0001_initial.py` imports it.
- `HistoricalDevice` has its own `qrcode` column (a CharField, because of
  `SIMPLE_HISTORY_FILEFIELD_TO_CHARFIELD`). The migration has to drop it
  together with the model's.

## Open follow-ups

- Delete `data/media/qrcode/` on every instance after step 3, and remove it
  from backups. This is in `NEWS.md`.

## Progress

- [x] **Step 1: the scanner honors the settings.**
  - `inventory/context_processors.py`: `qrCodeInfixes` in `js_vars`.
  - `qr_inventorize.js`:
    - a regex built from the prefix (escaped) and the infixes, any UUID
      version, hex digits in either case
    - `parseQrCode()` returns `{modelName, uuid}` or `null`
    - dispatch on `modelName`
    - ignore foreign codes, with no `alert()`
  - Update the QR section of `docs/guides/inventur.md`.
- [ ] **Step 2: the view renders the codes, the pages use it.**
  - `core/utils/qrcode.py`: `payload(model_name, uuid)` and `svg(payload)`
    (`make_qr(error="m")`), used by the view and by `uuid2qrcode`, which stays
    until step 3. Moved here from step 1, which is the scanner only.
  - `core/views/qrcode_views.py` and its route in `core/urls.py`.
  - Point every `….qrcode.url` at the view, in `_sidebar.html`,
    `rooms/detail.html`, `room_qrcodes_detail.html`, `qrvideo.html` and the
    `qrcode_display` of the device and room admins. Drop the
    `{% if ….qrcode %}` guards.
  - The QR code card on the rooms detail page links the room's printout
    (`inventory:qr-room-printout`, the room's code and those of its devices).
    The link shows only with `core.can_inventorize`, which the printout
    requires.
  - Tests for the view.
- [ ] **Step 3: the stored files go.**
  - Remove `qrcode` from `Device` and `Room`, and the `save()` overrides that
    fill it. One migration drops the column, also on `HistoricalDevice`.
  - Remove `QRCODE_DIR`, and its entries in `media_views`.
  - `test_media_views.py` uses other directories.
  - Remove the `generate_qrcodes` command and its docs row.
  - Remove `qrcode` from `audit_field_losses` and the `csv_export` comment.
  - Add a `NEWS.md` line.
  - Retire this plan into `DECISIONS.md`.
