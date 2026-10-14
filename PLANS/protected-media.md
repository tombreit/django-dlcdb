<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Protected media files

**Status:** planned (2026-10-14). Follow-up of `PLANS/login-required.md`. This is a living
document.

## Why

Since `PLANS/login-required.md` every page requires a login, but the uploaded and generated files
under `MEDIA_ROOT` bypass Django:

- **Source and pip installations:** Apache serves `/media/` itself, with `Alias /media` and
  `Require all granted` (`docs/betrieb/setup.md`). Anyone who reaches the server can fetch every
  file whose path they know or guess.
- **Container:** nothing serves `/media/`. `serve` runs only gunicorn, and `static()` in
  `dlcdb/urls.py` works only with `DEBUG`. QR codes and person images can only work there if the
  operator's reverse proxy serves the data volume.

What lies there (directory → model, screen that links it):

| Directory | Contents | Linked from |
|---|---|---|
| `person_images/` | HR photos (`Person.udb_person_image`, written by the UDB sync) | persons list and detail, smallstuff, person pickers (lending, device contact person) |
| `attachments/` | record attachments (`core.Attachment`) | record detail, record admin |
| `links/` | regulation files (`core.Link`) | printed lent sheet (`Link.display_url`), lending admin |
| `qrcode/` | device and room QR codes (SVG) | device sidebar, room detail, inventory QR printout, admin |
| `rooms_reconcile/` | Archibus CSV uploads (`core.RoomReconcile`) | room reconcile, admin |
| `branding/` | logos, licences logo, room plan (`organization.Branding`) | print pages, rooms list, inventory room list |
| `sap_csv/` | SAP inventory CSVs (`inventory.SapList`) | SAP comparison page, admin |
| `sap_list_comparison_results/` | SAP comparison results (written by `inventory/sap.py`) | SAP comparison page |
| `imported_csv/` | device import CSVs (`dataexchange.ImporterList`) | import detail |
| `toremove_csv/` | bulk decommission CSVs (`dataexchange.RemoverList`) | admin |
| `reporting/spreadsheets/` | report spreadsheets (`reporting.Report`) | report admin; mailed as attachment (read through the storage) |

## Decisions taken

1. **Django serves `/media/` in every installation.** A view under `MEDIA_URL` reads the file
   through the storage API (`default_storage`, whose `path()` refuses `..` traversal) and
   answers with a `FileResponse`.
   - `mod_wsgi` and gunicorn hand a `FileResponse` to `sendfile` via `wsgi.file_wrapper`, so no
     web-server module (`X-Sendfile`, `X-Accel-Redirect`) is needed.
   - The DEBUG-only `static()` route goes.
   - Operators remove the Apache `Alias /media`. As long as it stays, Apache answers before Django
     and the files stay public.
2. **Login first, then permissions.**
   - Batch 1: the login is enforced by the `LoginRequiredMiddleware`, like every page.
   - Batch 2: each directory requires the permission of the screen that links it, any one of
     several if several screens do.
3. **`links/` stays public.** The lent sheet prints each regulation's file URL for borrowers, who
   usually have no DLCDB login. It is the only public media directory, pinned by a test and named
   in the docs.
4. **Unknown directories are refused (404).** A test checks that every `FileField`'s upload
   directory, plus the directories code writes to directly, is known to the view. A new upload
   directory therefore needs a deliberate entry.
5. **Browser caching:** `Last-Modified` with conditional GET (304), and
   `Cache-Control: private, no-cache`. Shared caches keep nothing; browsers revalidate cheaply.
   Person images and QR codes are overwritten in place.
6. **No active content from uploads.** Media responses carry a restrictive
   `Content-Security-Policy`, so an uploaded HTML or SVG file opened directly cannot run script in
   the app's origin. QR codes are SVG. `X-Content-Type-Options: nosniff` already comes from
   `SecurityMiddleware`.

## Alternatives considered and rejected

- **`X-Sendfile` / `X-Accel-Redirect`.** It needs `mod_xsendfile` in Apache, or a specific nginx
  in front of the container. The files are small and few, and `wsgi.file_wrapper` already sends
  them efficiently.
- **`django.views.static.serve` behind a check.** Django documents it as a development aid only.
- **A registry each app fills from `AppConfig.ready()`** (like the device pickers). That is a new
  mechanism for about eleven directories that rarely change. One table next to the view, plus the
  coverage test, is enough.
- **A new `MEDIA_URL` prefix.** It does not protect anything while the old Apache `Alias` still
  exposes the directory.

## Open follow-ups

### Tenant scoping per file

Batch 2 checks permissions, not tenants. A user can fetch another tenant's attachment, QR code or
person image if they know its path. Scoping would map a path back to its object and run
`tenant_scoped_queryset`.

### Reporting spreadsheets over HTTP

They are mailed as attachments and only linked from the report admin. They might not need to be
served at all.

## Pitfalls

- **The Apache `Alias /media` must go**, in the source and pip installations alike. Django cannot
  detect it. NEWS and `docs/betrieb/setup.md` say so.
- **Every media file is now a Django request**: session and user lookup, tenant middleware. A
  persons list page with thumbnails makes one request per image. The 304s keep repeat visits
  cheap.
- **The CSP must not break what the browser shows inline:** `<img>` QR codes, person images,
  logos, PDFs. Check in a browser (batch 1).
- **`Link.display_url`** builds absolute URLs from `Site.domain` and `MEDIA_URL`. They keep
  working, since the path stays the same.
- **`inventory/models.py`** builds SAP result URLs by hand (`os.path.join(MEDIA_URL, …)`). They
  keep working too.

## Batches

### 1. Django serves media behind the login

- `dlcdb/core/views/media_views.py`:
  - the view: storage lookup, `FileResponse`, 404 for unknown directories and missing files;
  - `Last-Modified`/304, `Cache-Control`, CSP;
  - `login_not_required` handling for `links/`.
- `dlcdb/urls.py`: the route under `MEDIA_URL`; the DEBUG `static()` route goes.
- The public URL allowlist test (`accounts/tests/test_login_required.py`) learns the media route,
  public for `links/` only.
- `docs/betrieb/setup.md`:
  - remove the `Alias /media` block (source and pip installations);
  - the container section needs no media setup.
- NEWS, with the operator action.
- Tests:
  - anonymous: login redirect for `qrcode/…`, 200 for `links/…`;
  - logged in: 200 with content type and `Last-Modified`, then 304 on `If-Modified-Since`;
  - unknown directory, missing file and `..` traversal: 404 (or 400 for traversal);
  - the CSP header is set;
  - every upload directory is known to the view.
- Browser check: QR codes, person thumbnails, logos on print pages and a regulation PDF display.

### 2. Each directory requires the permission of its screens

Proposal, to re-check against the code at the start of the batch:

| Directory | Permission (any of) |
|---|---|
| `person_images/` | `core.view_person`, `smallstuff.view_assignedthing`, the lend transition permission, `core.change_device` |
| `attachments/` | `core.view_record` |
| `qrcode/` | `core.view_device`, `core.view_room`, `core.can_inventorize` |
| `rooms_reconcile/` | `core.view_roomreconcile` |
| `sap_csv/`, `sap_list_comparison_results/` | `core.change_inventory` |
| `imported_csv/` | `core.add_device` |
| `toremove_csv/` | `dataexchange.view_removerlist` |
| `reporting/` | `reporting.view_report` |
| `branding/` | login only (organization-wide, printed on every sheet) |
| `links/` | public |

- The table sits next to the view. A missing permission answers like
  `htmx_permission_required`: a 403 that names the permission.
- Tests:
  - per directory, a user without the permission is refused and a user with it gets the file;
  - the coverage test now requires an entry per directory.
- NEWS.

## Progress

- [x] **0. This document**
- [ ] **1. Django serves media behind the login**
- [ ] **2. Each directory requires the permission of its screens**
