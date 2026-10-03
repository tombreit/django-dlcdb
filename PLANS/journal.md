<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Journal: one log for all in-app logs

**Status:** implemented on branch `unified-logging` (batches 0–7, 2026-10-03), after reviews of
the journald fields and of existing Django packages. The legacy logs are still written in
parallel (decision 2); see *Phase-out of the legacy logs* and *Open follow-ups* for what is
left. This is a living document.

## Why

DLCDB keeps its operation logs in several places, each with its own format and table:
- `ImporterList` (import log), `RemoverList` (decommissioning log) and `UdbSyncRun` (HR sync log),
  all on `OperationLogBase` (`dataexchange/models.py`);
- `notifications.Message` (sent/failed status and error text for each mail);
- custom admin `LogEntry` writes (UDB sync changes per person, Activated/Deactivated, device-note
  changes).

Runtime anomalies that the code already marks (`logger.warning/error/exception`, unhandled
exceptions in views and huey tasks) reach only the console.

There is no single view of any of this. The new app `journal` (after journald; the name `logging`
stays reserved for Django's `LOGGING`) gets one append-only schema and one filterable list.
Emitters move over one at a time.

## Decisions taken

1. **App `dlcdb.journal`, model `JournalEntry`, permission `journal.view_journalentry`, URL
   `/journal/`.** The nav entry goes in *Settings*.
2. **Dual write, journal first.** The journal is the view to use. Moved emitters keep writing
   their old logs in parallel, for debugging and comparison. Old tables, admin pages and the
   import history stay unchanged until they are phased out (see *Phase-out of the legacy logs*).
3. **Stage 1 is verbatim:** the old log text goes into `body` unchanged.
4. **Append-only, one entry per event.** The old rows overwrite their log on each attempt; the
   journal records every attempt. Exception: a mail retry that fails again is not journaled
   (batch 6).
5. **Tenant + global visibility.** An entry has an optional tenant. Viewers see the entries of
   their tenants plus tenant-less entries, which are system events such as HR sync runs and
   anomalies, not orphans. That is why the journal does not use `tenant_scoped_queryset`. Import
   entries carry the import's tenant.
6. **HR sync: only runs with changes.** A run is journaled if any row is not `UNCHANGED`. A failed
   run counts, through its `<sync>` error row, and so does a run with per-contract errors, every
   time (confirmed with the user, see *Open questions*).
7. **`source` is free text** of the form `<app_label>.<topic>` (`dataexchange.import`,
   `dataexchange.decommission`, `dataexchange.hr_sync`, `notifications.mail`, `core.admin`,
   `accounts.admin`). No choices: a new emitter needs no migration. The filter offers the distinct
   values found in the DB.
8. **Explicit emitter calls.** No signals, no hook in `OperationReport.persist()`.
9. **Each emitter batch copies its existing rows** in a data migration that lives in the source
   app and ships with the live emitter. That way there is never a gap or duplicate window, however
   often it is deployed.
10. **`level` uses syslog numbers** (journald `PRIORITY=`): CRITICAL=2 (only from Python logging),
    ERROR=3, WARNING=4, SUCCESS=5 (takes syslog "notice") and INFO=6. Lower means more severe.
    Sorting works, and "warnings and errors" is `level__lte=WARNING`, like
    `journalctl -p warning`.
11. **`event` names the kind of entry** (journald `MESSAGE_ID=`): a short slug within its source,
    such as `imported`, `dry_run_failed` or `failed`. Filters and queries use `event`, never
    summary text. It is free text like `source`, and the filter offers the distinct values.
12. **The user is whoever caused the event** (journald `_UID=`). For example, the entry for an
    import names whoever wrote it, not the uploader stored on the `ImporterList` row. Runs nobody
    triggered have no user.
13. **Entry text is data, stored as written** (journald: `MESSAGE=` is "usually not translated").
    `summary` and `body` are never translated on display; only UI labels (field names, level and
    filter labels) are.
    - `log()` renders lazy strings under `translation.override(None)`, like the admin's
      `construct_change_message`, so they are stored untranslated.
    - Plain `gettext` text keeps the language active at write time, and so do the existing
      `LogEntry` rows (relevant for batch 7's copy).
    - That is one more reason filters use `event`, not wording.
14. **Anomalies come in through Python logging.** A `JournalHandler` (`journal/handlers.py`) is
    attached in `LOGGING`; the existing log calls stay unchanged (see *Anomalies from Python
    logging*):
    - `dlcdb`: WARNING and above;
    - `django.request`: ERROR and above, i.e. unhandled exceptions in views (500), with the user
      from `record.request`;
    - failed huey tasks: a `SIGNAL_ERROR` receiver logs them to `dlcdb.huey` with the task name.

    Anomaly entries are tenant-less, so every journal viewer sees them (decision 5). We decided
    against a separate permission for them.
15. **A fact is journaled once.** A log call whose fact an emitter journals itself passes
    `extra={"journal": False}`.
16. **Repeated anomalies are journaled once per hour** (journald rate limiting). An anomaly with
    the same source, level and summary as an entry from the last hour is skipped. The console
    keeps every occurrence. Explicit events are never skipped.
17. **Journaling an anomaly never breaks the caller.** The handler:
    - writes in a savepoint;
    - skips when the surrounding transaction is already broken;
    - hands its own errors to `Handler.handleError`.

    An anomaly logged inside a transaction that later rolls back is lost from the journal, not
    from the console. Explicit `log()` calls are not guarded: a missing audit entry must fail
    loudly.

## Schema

`JournalEntry` (BigAutoField):

| Field | Type | Notes |
|---|---|---|
| `timestamp` | DateTimeField(`default=timezone.now`, db_index) | not `auto_now_add`, see *Pitfalls* |
| `source` | CharField(100, db_index) | decision 7 |
| `event` | CharField(50, db_index) | decision 11 |
| `level` | PositiveSmallIntegerField, `Level(IntegerChoices)`: CRITICAL=2, ERROR=3, WARNING=4, SUCCESS=5, INFO=6 | decision 10, default INFO |
| `summary` | CharField(255, blank) | one line, shown in the list |
| `body` | TextField(blank) | verbatim in stage 1 |
| `user` | FK user, null, SET_NULL, `related_name="+"` | decision 12 |
| `username` | CharField(255, blank) | denormalized, like `AuditBaseModel` |
| `tenant` | FK `tenants.Tenant`, null, PROTECT | same as `ImporterList.tenant` |
| `content_type`, `object_id` (PositiveBigIntegerField, null), `content_object` (GFK), `object_repr` | optional subject | like Django's `LogEntry`, but with an integer `object_id`: every DLCDB primary key is an integer, so joins need no casts |

- `ordering = ["-timestamp", "-pk"]`.
- `JournalEntry.objects.log(*, source, event, summary, body="", level=Level.INFO, user=None,
  username=None, subject=None, tenant=None)` adds one entry, the same idiom as
  `LogEntry.objects.log_actions`.
  - `username` defaults to `str(user)`.
  - `object_repr` defaults to `str(subject)`.
  - `tenant` defaults to `subject.tenant` when the subject has one.
- The journal imports no emitter app.

For `OperationLogBase` emitters, one method on the abstract base does the mapping. Each concrete
model sets `journal_source`:

```python
# OperationLogBase.Status -> JournalEntry.Level; an empty status (never confirmed) is INFO.
JOURNAL_LEVELS = {
    OperationLogBase.Status.SUCCESS: JournalEntry.Level.SUCCESS,
    OperationLogBase.Status.WARNING: JournalEntry.Level.WARNING,
    OperationLogBase.Status.ERROR: JournalEntry.Level.ERROR,
}


def write_journal(self, *, event, user):
    """Copy the stored outcome into the journal, verbatim (stage 1).

    ``user`` is whoever caused this event (decision 12), not necessarily the row's user.
    """
    return JournalEntry.objects.log(
        source=self.journal_source,
        event=event,
        level=JOURNAL_LEVELS.get(self.status, JournalEntry.Level.INFO),
        summary=self.summary,
        body=self.messages,
        user=user,
        subject=self,
    )
```

### journald mapping

| journald | journal |
|---|---|
| `MESSAGE=` | `summary` (first line) + `body` |
| `MESSAGE_ID=` | `event` |
| `PRIORITY=` | `level` |
| `SYSLOG_IDENTIFIER=` | `source` |
| `_UID=` | `user` / `username` |
| `OBJECT_*=`, `UNIT=` | subject (`content_type`, `object_id`, `object_repr`) |
| `CODE_FILE=`, `CODE_LINE=`, `CODE_FUNC=` | in the body of anomaly entries |
| `__REALTIME_TIMESTAMP=` | `timestamp` |
| `__CURSOR=`, `__SEQNUM=` | `pk` |
| none | `tenant` (DLCDB visibility, decision 5) |

## Events

| Source | Events |
|---|---|
| `dataexchange.import` | `imported` (a write, with its report's level), `dry_run_failed` (a dry run found bad rows or raised), `failed` (a write raised and rolled back) |
| `dataexchange.decommission` | `decommissioned` |
| `dataexchange.hr_sync` | `synced`, `sync_failed` (run-level failure); no entries per person (batch 7) |
| `notifications.mail` | `sent`, `failed` |
| `core.admin` | `activated`, `deactivated`, `device_note_changed` |
| `accounts.admin` | `deactivated` |
| any logger (`dataexchange.udb_sync`, `notifications.channels`, `django.request`, `huey`, …) | `log`, `exception` (the record carries a traceback) |

## Anomalies from Python logging

`journal/handlers.py` is referenced from `LOGGING` by dotted path. `LOGGING` is applied before the
app registry is ready, so the module imports no models at import time. Sketch:

```python
_emitting = ContextVar("journal_emitting", default=False)
REPEAT_WINDOW = timedelta(hours=1)


class JournalHandler(logging.Handler):
    """Copy log records into the journal (decisions 14-17)."""

    def emit(self, record):
        if getattr(record, "journal", True) is False or _emitting.get() or not apps.ready:
            return
        token = _emitting.set(True)  # a log call while writing must not recurse
        try:
            if connection.in_atomic_block and transaction.get_rollback():
                return  # broken transaction: every query would fail
            entry = entry_from_record(record)
            if not is_repeat(entry):
                with transaction.atomic():  # savepoint: a failed insert leaves the caller's transaction intact
                    entry.save()
        except Exception:
            self.handleError(record)
        finally:
            _emitting.reset(token)
```

- `entry_from_record(record)` is a pure function that maps a log record to an unsaved entry:
  - `source`: the logger name without `dlcdb.` (`dataexchange.udb_sync`, `django.request`,
    `huey`);
  - `event`: `exception` when the record carries `exc_info`, otherwise `log`;
  - `level`: CRITICAL, ERROR or WARNING, mapped to `Level`;
  - `summary`: the first line of the message, cut to 255 characters;
  - `body`: the message, then `pathname:lineno in funcName`, then the formatted traceback;
  - `user`: from `record.request` when it is authenticated (`django.request` sets it).
- `is_repeat(entry)`: an entry with the same source, level and summary exists since
  `now - REPEAT_WINDOW` (decision 16).
- `LOGGING` in `dlcdb/settings/base.py`:
  - handlers `journal` (level WARNING) and `journal_errors` (level ERROR), both
    `dlcdb.journal.handlers.JournalHandler`;
  - `dlcdb` gets `["console", "journal"]`;
  - `django.request` gets `["journal_errors"]`, with no level of its own and `propagate: True`, so
    404/403 warnings still reach the console and 500s still reach `mail_admins`.
- `journal/signals.py`, imported in `JournalConfig.ready()`:

  ```python
  @signal(SIGNAL_ERROR)
  def log_task_error(signal, task, exc=None):
      logging.getLogger("dlcdb.huey").error("Task %s failed: %s", task.name, exc, exc_info=exc)
  ```

  Huey's own line names only the task id. This one goes through the same handler, so decisions
  15–17 apply.

## Views

- **`journal_index`** (`/journal/`, `@permission_required("journal.view_journalentry",
  raise_exception=True)`):
  - built like `rooms/views.py:room_index`: htmx partial, `data.setdefault("ordering",
    "-timestamp")`, `paginate()` with 50 per page, `build_filterbar()`;
  - filter:
    - `search` over summary, body, username, object_repr and source;
    - `source` and `event`: ChoiceFilters with callable choices over the distinct values in the
      DB;
    - `level`: "Minimum level" (`level__lte`, decision 10);
    - ordering by timestamp, source and level;
  - columns: time, level badge, source and event, summary (links to the detail page), user.
- **`journal_detail`** (`/journal/<pk>/`), read-only and scoped like the list:
  - metadata and `<pre>` body;
  - the subject as a link if `content_object` has `get_absolute_url`, otherwise `object_repr`;
  - back link via `theme.navigation.index_url`.
- Templates extend `theme/_index_base.html` (with their own `partialdef`) and
  `theme/_detail_base.html`. Classes only, no template tags. `journal/includes/_level_badge.html`
  has the same structure as `dataexchange/includes/_status_badge.html`.
- No admin registration for now.

## Progress

- [x] **0. This document**
- [x] **1. Journal app**
  - model, manager, `journal/0001_initial`, views, filter, templates;
  - `navigation.py` (`nav_settings`, `bi bi-journal-text`);
  - `LOCAL_APPS`, `dlcdb/urls.py`;
  - nav/permission table in `docs/guides/berechtigungen.md`, NEWS.
  - Tests:
    - manager defaults, including a lazy string stored untranslated;
    - 403 without the permission;
    - list and htmx fragment;
    - search, source, event and minimum-level filters;
    - sorting by level orders by severity;
    - another tenant's entry hidden, tenant-less entry visible;
    - detail scoped the same way.
- [x] **2. Anomalies from Python logging** (decisions 14–17)
  - `journal/handlers.py`, `journal/signals.py`, `JournalConfig.ready()`;
  - `LOGGING` in `dlcdb/settings/base.py`;
  - NEWS.
  - Tests in `journal/tests/test_handlers.py`:
    - a `dlcdb.*` warning adds one `log` entry; `logger.exception` adds an `exception` entry with
      the traceback in its body;
    - INFO and `extra={"journal": False}` add none;
    - the same anomaly twice within the hour adds one entry;
    - inside a broken atomic block: no entry, no exception, the caller's transaction is unharmed;
    - a failing insert does not raise from the log call;
    - a 500 response adds a `django.request` entry with the user;
    - the huey receiver logs the task name;
    - the outside-atomic path is tested with `transaction=True` (see *Pitfalls*).
- [x] **3. Import log** (`dataexchange.import`)
  - `OperationLogBase.write_journal()` and `JOURNAL_LEVELS`; `ImporterList.journal_source`.
  - `run_device_import` (`importer.py`) takes the acting `user` instead of `username` and
    passes `user.username` down. All four callers have `request.user`: the two frontend views,
    the admin `save_model` and `ImporterAdminForm.clean`.
  - Journal calls in `run_device_import`:
    - after the error-path `save()`: `failed` (write) or `dry_run_failed` (dry run);
    - after `report.persist()`: `imported` (write) or `dry_run_failed` (dry run with bad rows).
  - This covers frontend confirm, dry runs with errors and admin `save_model`.
  - The importer's per-row warnings (build and write passes) get `extra={"journal": False}`
    (decision 15). They repeat the import entry's per-row lines and fire inside transactions that
    roll back.
  - `ImporterList.get_absolute_url()` pointing to `dataexchange:importer_detail` (also adds
    "View on site" in the admin).
  - Migration `dataexchange/0009`:
    - copies rows with non-empty `messages`; timestamp `modified_at`; tenant copied over;
    - user and username come from the row (the uploader), since an old row does not know who
      wrote it;
    - event derived from the log text: `(dry run)` in the first line → `dry_run_failed`,
      prefix `Import failed:` → `failed`, otherwise `imported`.
  - Tests:
    - write, failed dry run and exception add one entry each, with the right event, level,
      tenant and acting user;
    - a clean dry run adds none;
    - migration test.
- [x] **4. Decommissioning log** (`dataexchange.decommission`)
  - `RemoverList.journal_source`; `write_journal(event="decommissioned", user=request.user)`
    after `report.persist(obj)` in `RemoverListAdmin.save_model`.
  - Migration `dataexchange/0010`. Tests.
- [x] **5. HR sync log** (`dataexchange.hr_sync`)
  - `UdbSyncRun.journal_source`.
  - `udb_sync._store_run` gets the event: `sync_failed` from the run-level `except`, `synced`
    otherwise. It calls `write_journal(event=…, user=None)` per decision 6.
  - "Failed to import UDB contract" and "[UDB] sync failed" in `udb_sync.py` get
    `extra={"journal": False}`, because the run entry carries both. The fetch errors stay
    journaled: their text (HTTP status, server response) is more detailed than the run entry's.
  - Pruning stays at 50 runs.
  - Migration `dataexchange/0011`:
    - skips unchanged-only runs (success and summary `"N unchanged"` / `"no rows"`);
    - a `<sync>` row in the log → `sync_failed`, otherwise `synced`.
  - Tests: changes → one entry; all unchanged → none; failed run → one `sync_failed`.
  - Implemented last: it waited for the answer under *Open questions*.
- [x] **6. Notification mails** (`notifications.mail`)
  - `sent` entry in `EmailChannel.send` (body To/Cc). `failed` entry in `mark_message_failed`
    (body = `error_message`).
  - Journal a mail only when its status changes (pending → sent or failed, failed → sent). A
    failed message is retried every minute, and a retry that fails again is not journaled
    (decision 4).
  - "No recipient email address" and "Failed to send email" in `channels.py` get
    `extra={"journal": False}` (decision 15).
  - Subject = Message. Tenant = `subscription.device.tenant` when there is one. No user: mails
    are sent by tasks.
  - Migration `notifications/0004`: copies sent messages (timestamp `sent_at`) and failed ones
    (`modified_at`).
  - Mails without a tenant (overdue lenders, reports) are journaled without one and are visible
    to every journal viewer, like anomalies (decided with the user, 2026-10-03).
- [x] **7. Custom admin actions** (`core.admin`, `accounts.admin`; the LogEntry rows stay, the
  journal gets a copy)
  - `SoftDeleteModelAdmin.activate_view/deactivate_view` (events `activated`, `deactivated`) and
    the device note in `LicenceRecordAdmin.save_model` (`device_note_changed`) → `core.admin`.
  - `accounts/admin.py` deactivate → `accounts.admin`, event `deactivated`.
  - Migration `core/0078`:
    - copies LogEntry rows with the exact messages `Activated` / `Deactivated` / `Deactivated.`
      and the prefix `Device note changed.`;
    - event from the same match;
    - uses `action_time`, `object_repr` and content type/id as they are; tenant only for device
      subjects.
  - **No UDB entries per person** (decided with the user, 2026-10-03: start small). The HR sync
    is covered by its run entry (batch 5). Its body lists the notable changes briefly: one line
    per created, updated, skipped or failed person; unchanged rows and the field diff only with
    DEBUG. The per-person diff stays in the admin History tab (`LogEntry` "Changed by UDB sync:
    field: old -> new"); Person has no simple-history.

Every batch:
- `.venv/bin/pytest .` green;
- `manage.py makemigrations --check --dry-run` clean;
- `/verify` against a scratch DB:
  - `/journal/` with and without the permission;
  - tenant scoping;
  - filters;
  - detail page and subject link;
  - from batch 2 on, trigger an anomaly (e.g. HR sync against an unreachable URL) and check its
    entry;
  - from batch 3 on, import a file and check the new entry;
- data migrations also run forward against a copy of a real DB, comparing counts.

## Working agreement

Agreed with the user on 2026-10-03, for implementation while they are away:
- **Commit after each batch,** once it is checked and tested (pytest, `makemigrations --check`,
  pre-commit, `/verify`); don't push.
- **Commit messages are one line,** `Journal, step N: …`, and make sense without this document.
- **Decide alone only when very confident** that the choice is right and fits the codebase and
  its style, and record it under *Decided during implementation*.
- **Otherwise,** record the open question there, move the affected batch to the end, and continue
  with a batch that doesn't depend on it.

## Open questions

None. Answered:
- **Batch 5, HR sync runs with persistent per-contract errors** (found 2026-10-03). In
  production every run carries the same 3 failing contracts ("257 unchanged, 3 error", all 50
  stored runs, 2026-08-18). The options were to journal error-only runs once until the errors
  change, once per hour, or every time. **The user chose every time:** decision 6 stands as
  written, and a contract that keeps failing is journaled with every run, 144 entries a day
  while it fails.

## Decided during implementation

- **Batch 1, detail page on `theme/_base.html`,** like `dataexchange/importer_detail.html`, not
  on `theme/_detail_base.html`. That frame is built around a form, and its docstring says pages
  that are read-only by design don't use it.
- **Batch 1, source and event choices are set in `JournalEntryFilter.__init__`,** not as
  callable `choices`: django-filter's `ChoiceIterator.__len__` calls `len()` on them, which a
  callable doesn't support.
- **Batch 1, `_subject_url()` checks `content_type.model_class()`** before touching
  `content_object`. Once a legacy log model is retired (`UdbSyncRun`, see *Phase-out*), its
  content type has no model class and the GFK would raise. It also treats a `None` from
  `get_absolute_url()` as "no page" (a `Device` has one only as a licence).
- **Time-dependent test failures,** unrelated and left alone. Both failed on a clean checkout of
  `7ccc178` around 01:00 on 2026-10-03 and passed in later runs:
  - `assets/tests/test_devices.py::DeviceFrontendTests::test_modified_column_uses_naturaltime_for_recent_edits_only`;
  - `core/tests/test_form_round_trip.py::test_edit_page_renders_and_round_trips_every_field[lending_return]`.
- **Batch 3, old import logs without status** (production, 29 rows: "Imported devices: N",
  written before `status` existed) are copied as `imported` at level INFO: the status is
  unknown, and the copy stays verbatim. The import report's row details mix German and English
  (some importer strings are translated at write time); the journal copies that verbatim too.
- **Batch 3, the frontend tests that drive an import** pass the acting user as `user=`; the
  importer still resolves the audit `user` FK from `user.username` (unchanged hard lookup).
- **Batch 4, decommissioning entries have no tenant,** so every journal viewer sees them.
  `RemoverList` has no tenant and its admin is not tenant-scoped (everyone with
  `view_removerlist` sees every run), and one file may cover devices of several of the
  uploader's tenants. This keeps today's visibility rather than inventing a tenant. A failed run
  still raises before anything is stored (unchanged); then there is no entry either.
- **Batch 6, every successful send is journaled,** including a manual resend of an already
  sent message (admin "send now"): each one is a mail that went out. Only failures are limited
  to the transition into "failed", which is what stops the retry flood.
- **Batch 6, the `sent` entry is written after the `try` block** in `EmailChannel.send`, so a
  journal error cannot flip a sent message to "failed" through the channel's catch-all.
- **Batch 6, copied mails** (production: 296 sent, none failed, 2 pending skipped) get the
  recipient the way `Person.get_email` picks it. Their subject text is
  `"<id> - <status> - <recipient or subscription id>"`, because a historical model lacks
  `Subscription.__str__`.
- **Batch 7, summaries** are `"Activated <model>: <object>"` / `"Deactivated <model>: <object>"`
  with the untranslated model name (`room`, `device`, …), `"Device note changed"` (the admin
  history text goes into the body) and `"Deactivated user: <email>"`. A device subject brings
  its tenant through `log()`'s subject default; persons, rooms, device types and users have
  none.
- **Batch 7, the copy matches `Deactivated.` in English only:** the msgid has no translation in
  `dlcdb/locale`, so gettext always stored it as is. Production: 17 rows (14 deactivations,
  3 device note changes); the copied `username` is the actor's email, `CustomUser.__str__`.
- **Batch 5, the copy keeps all 50 production runs:** each has per-contract errors, so none is
  unchanged-only. Two runs that failed during the batch 2 check on the scratch DB show that an
  anomaly journaled before batch 5 ("[UDB] sync failed") and the copied `sync_failed` run entry
  describe the same failure. That only affects history from before this batch; from now on the
  log line opts out (decision 15).
- **Unrelated finding (batch 2):** a 500 now runs `mail_admins` in the handler test, which shows
  Django's `RemovedInDjango70Warning`: `ADMINS` holds `(name, address)` pairs
  (`dlcdb/settings/base.py`). Left alone.

## Lessons from existing packages

Reviewed 2026-10-03 as sources of ideas only; none of them will be used.

| Package | Borrowed | Left out |
|---|---|---|
| django-db-logger | lazy model import in `emit`; logger name as source; traceback kept with the entry | its unguarded `emit`: no recursion guard, and DB errors raise from the caller's `logger.error()` |
| django-eventlog | per-operation group UUID (follow-up) | dynamic `e.info()` API via `__getattr__`; mail sending inside the log call |
| django-activity-stream | one subject GFK; untranslated stored text | actor/target/action_object triple; CharField object ids, which cost index use |
| django-auditlog | snapshots that survive deletion (`username`, `object_repr`); integer `object_id`; flush command with `--before` (follow-up) | `remote_addr` from `X-Forwarded-For` (spoofable); a signal connected and disconnected per request; flush via `timestamp__date`, which cannot use the index |
| Wagtail audit log | `event` slug per kind (decision 11); event label registry (follow-up); per-operation UUID via a context (follow-up) | messages formatted from JSON data at display time (stage 2); `full_clean()` on every save; silently dropped writes |
| django-easy-audit | journal errors never break the caller (decision 17, anomalies only); login events (follow-up) | `on_commit` writes, which lose what rolled back; session parsing on every request |
| django-pghistory, django-structlog | request/operation context in a ContextVar (follow-up) | Postgres triggers; the structlog dependency |
| Django admin `LogEntry` | `translation.override(None)` for stored text (decision 13) | JSON change messages translated at display time (stage 2) |
| Bugsink / Sentry | none | full error tracking (grouping, stack locals, alerts) is out of scope: the journal records *that* something went wrong |

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| `post_save` signals on the old log models | Implicit. They would fire on unrelated saves too (tenant assignment touches `ImporterList.modified_at`). |
| Hook in `OperationReport.persist()` | Misses the importer's error path, which writes the row directly. `persist()` doesn't know the source, and the HR sync filter (decision 6) doesn't belong there. |
| `source` as TextChoices | Every new emitter would need an `AlterField` migration, and the journal would have to know all its emitters. |
| `level` as text with the values of `OperationLogBase.Status` | Sorts alphabetically (error, info, success, warning) and cannot express "warnings and errors". |
| 128-bit `MESSAGE_ID` like journald | journald needs IDs that are unique across all programs. Within one app, a slug per source is enough and readable. |
| Telling event kinds apart by summary text | Breaks on rewording, and text translated at write time is in mixed languages (decision 13). |
| The row's user (the uploader) on every import entry | Wrong actor for the write; decision 12. |
| `JournalEntry(AuditBaseModel)` | `auto_now_add` overwrites copied timestamps; `modified_at` is meaningless for append-only rows. |
| Copy migrations in the journal app | Couples the journal to every emitter. A later "drop old log table" migration would need a cross-app dependency to run after the copy. |
| One copy migration in batch 1 for all three operation logs | Logs written between that deploy and the emitter batches would never be copied. |
| django-auditlog / django-reversion / simple-history as the journal | Those record model field changes, not operation events with free-text bodies. simple-history stays for per-model field history. |
| Buffering anomalies raised inside transactions and flushing them after the request, task or command | Needs flush points in middleware, huey and every management command. Only the importer's per-row warnings fire in transactions that roll back, and decision 15 excludes them. |
| A second DB alias or a separate SQLite file for the journal | On SQLite a second connection waits on the request's own write lock ("database is locked"). A separate file rules out FKs to user, tenant and content type, and every test needs both databases. |
| `QueueHandler` + listener thread | A thread to start and stop per process (gunicorn workers, huey consumer), and on SQLite it still waits for the write lock. |
| `transaction.on_commit` for anomalies | Drops exactly the anomalies that came with a rollback. |
| Attaching the handler to the `huey` logger | Huey's line names only the task id, which also defeats decision 16. |
| Swallowing errors in explicit `log()` calls | Would hide missing audit entries; an insert into the same DB fails only when the DB itself fails. |
| A separate permission for anomaly entries | Decided against: journal viewers are admins; one more permission and queryset branch for little gain. |
| Other journald fields | `CODE_FILE`/`LINE`/`FUNC` as fields break on every refactor; anomaly entries carry the code location in their body. `ERRNO`, process, kernel and host fields have nothing to map to in one Django app with one DB. `DOCUMENTATION=` would belong to an event type rather than an entry. `_TRANSPORT`/`_COMM` (web, task, command) would need a parameter through every entry point. |

## Open follow-ups

- **Inventory note appends** (`inventory/utils.py:update_inventory_note`,
  `core/models/inventory.py`): a candidate emitter.
- **Silent broad handlers** worth a logger call, so they reach the journal through decision 14:
  - `licenses/views.py`: a save error is shown to the user with its stack trace, never logged;
  - `core/admin/base_admin.py`: the silent `get_queryset` fallback;
  - `inventory/management/commands/verify_lendings.py`: the SMTP error is printed and
    swallowed;
  - `notifications/tasks.py`: the result of `send_message` is ignored.
- **Login events** (`user_logged_in`, `user_login_failed`): a failed login is a notable thing too.
- **Stage 2, structured bodies:** e.g. per-row results as JSON instead of verbatim text
  (journald: "new fields may freely be defined by applications").
- **Event labels:** translated labels per `event` slug (Wagtail's registry), e.g. a dict per app
  auto-discovered like `navigation.py`.
- **Correlation** (journald `INVOCATION_ID=`): a nullable UUID shared by the entries of one
  request or run, set from a ContextVar by middleware and passed explicitly into huey tasks,
  since huey doesn't propagate contextvars. Not needed while the HR sync writes only run entries.
- **Per-object journal** on the device, person or import detail page: needs an index on
  `(content_type, object_id)`. It is a prerequisite for phasing out `ImporterList.messages`.
- **Retention/purging,** if volume grows (decisions 6 and 16 keep it small): a command
  `journal_flush --before <date>` deleting in batches by `timestamp__lt`.
- **`recorded_at`** (`auto_now_add`, journald `__REALTIME_TIMESTAMP=` vs
  `_SOURCE_REALTIME_TIMESTAMP=`): would show copied entries, whose `timestamp` is only
  approximate, as copies. Low value.

## Phase-out of the legacy logs

Not part of the batches above. Each legacy log is phased out on its own, once its emitter batch
has run in production long enough to show that the journal and the legacy log agree, apart from
the intended differences under *Pitfalls*. Most legacy "logs" are workflow or queue objects with
log fields, so phasing out mostly means dropping fields and admin views, not tables:

| Legacy log | What can go | What stays, and why |
|---|---|---|
| `UdbSyncRun` | the model and its admin, the pruning (`MAX_STORED_SYNC_RUNS`); the link in the `UdbSyncConfiguration` change form points to `/journal/?source=dataexchange.hr_sync` instead | nothing; it is a pure log |
| `ImporterList` | `messages`, perhaps `summary`; the import detail page shows the journal entries whose subject is the import (per-object journal) | the row: file, tenant, `imported_by` on devices, and `status`, which the confirm guard reads (`device_import_confirm`) |
| `RemoverList` | `messages` (its admin form shows it read-only; a link to the journal entries replaces it); `summary` and `status` (nothing reads them) | the row: the uploaded file and note |
| `notifications.Message` | nothing yet | it is the mail queue: `status` drives sending and retries |
| Custom `LogEntry` writes | the copies only, if the admin History tab may lose them | they feed the admin History tab (`PersonAdmin` is not a `SimpleHistoryAdmin`) |

- A drop migration goes into the source app after its copy migration, so the order is guaranteed
  without cross-app dependencies (decision 9).
- Once `messages` is gone, `OperationReport.persist()` only fills the remaining fields, or goes
  away together with them.

## Pitfalls

- **Expected differences during the parallel phase:** they are not bugs when comparing journal
  and legacy logs:
  - the legacy import row holds only the latest attempt, the journal every attempt
    (decision 4);
  - the legacy import row names the uploader, the journal entry the acting user (decision 12);
  - `UdbSyncRun` keeps every run (the last 50), the journal only runs with changes
    (decision 6);
  - a mail retry that fails again updates `Message.error_message` but adds no journal entry
    (batch 6);
  - the console shows every repeated anomaly, the journal one per hour (decision 16).
- **`timestamp` must not be `auto_now_add`.** Historical models keep field options, so the copy
  migrations would get the migration time instead of the original one.
- **Historical models have no custom methods.** The copy migrations build `object_repr`
  themselves: the file name for imports and decommissions, `HR API Sync Run <date> (<status>)`
  for runs.
- **Copy migrations derive `event` from old log text.** That works because the text comes from
  `OperationReport` and the importer in untranslated English. The batch 7 LogEntry match also
  has to cover `Deactivated.` in every language it may have been stored in (decision 13).
- **Copy migrations reverse as `noop`.** Re-applying after a rollback duplicates entries.
- **`tenant` is PROTECT.** With SET_NULL, a deleted tenant's entries would become global
  (decision 5).
- **Pruned `UdbSyncRun` rows** leave entries whose GFK points to nothing. `object_repr` keeps
  them readable.
- **Importer error path:** the journal write must run after the failed write's transaction has
  rolled back, which is where the row's error `save()` already happens. Otherwise the entry
  rolls back too.
- **Never attach the handler to `django.db.backends` or below WARNING.** Every SQL statement
  would recurse into an insert, and django-db-logger users had `migrate` hang that way.
- **Web workers and the huey consumer both run the handler** and write the same SQLite file:
  normal write contention, no new lock.
- **Before the journal table exists** (the first `migrate`), an anomaly's insert fails and lands
  in `handleError` on stderr. Harmless.
- **Tests:** `TestCase` runs everything inside a transaction, so the handler's outside-atomic
  path needs `transaction=True` tests. If no-DB tests log `dlcdb` warnings, the handler would
  hit pytest-django's DB guard and print a logging error; then the test settings detach the
  journal handlers.
- **The list must not touch `content_object`.** A GFK cannot be `select_related`, so it would
  cost one query per row; the list shows `object_repr`.
