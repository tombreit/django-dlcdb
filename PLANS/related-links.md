<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Related links: open or add the object a select points to

**Status:** planned 2026-10-15, batch 1 added 2026-10-16; batch 1 done (one `?next=`), the
buttons themselves not yet. This is a living document: each batch ticks its box under *Progress*
and updates this line in the same commit.

## Why

In the admin, a foreign-key or many-to-many select has icons next to it: change, add, view (and
delete). In the frontend the same select is a dead end. If the manufacturer is missing, the user
has to leave the device form, go to *Master data › Manufacturers*, add it there, and find the way
back to the device.

The frontend gets the same buttons, without the admin's popup. They open our existing pages for
device type, manufacturer, supplier, room and person, and those pages lead back to the form with
the new object preselected.

## Design

### What the user sees

     Manufacturer
     ┌────────────────────────────┐┌───┬───┐
     │ Dell                     ▾ ││ ✎ │ + │
     └────────────────────────────┘└───┴───┘

- ✎ edits the selected manufacturer. Without the change permission it is 👁, which views it. It
  is disabled while nothing is selected.
- \+ adds a manufacturer.
- The buttons are attached to the select in a Bootstrap `input-group`. Each has a `title` and
  visually hidden text.
- ✎ follows the selection.
- The links open in the same tab. If the form has unsaved input, a confirm dialog asks first.

### The round trip

1. On the device page `/assets/devices/12/?next=…` the user clicks + next to *Manufacturer*.
2. This opens `/assets/manufacturers/add/?next=/assets/devices/12/%3Fnext%3D…&next_field=manufacturer`.
3. Saving redirects to `next` with `manufacturer=<new pk>` set:
   `/assets/devices/12/?next=…&manufacturer=42`. The message "Manufacturer “Dell” was created."
   appears there.
4. The device form preselects manufacturer 42. Nothing is stored on the device until the user
   saves it.

✎ works the same way, without `next_field`. On the manufacturer page, Save, Back and Cancel return
to `next`.

Unsaved input on the device form is lost on the way; the dialog in step 1 says so. A preselected
value survives the next round trip, because it is part of the URL that the trip returns to: + on
*Supplier* after coming back keeps `manufacturer=42`.

## What we take from the Django admin

What the admin has, in Django 6.1.1 (`.venv`, `django/contrib/admin/`):
- `widgets.py:264` `RelatedFieldWidgetWrapper` wraps any widget and renders it plus the links
  (`admin/widgets/related_widget_wrapper.html`).
- `options.py:213` `formfield_for_dbfield` wraps every FK and M2M form field whose related model
  is registered. The `can_*` flags come from the permissions of the related ModelAdmin.
- `RelatedObjectLookups.js`:
  - on `change`, it fills the change and view hrefs from `data-href-template`, replacing the
    `__fk__` placeholder, and sets `aria-disabled` when the select is empty;
  - the popup protocol (`_popup`, `popup_response.html`, `dismiss*RelatedObjectPopup`) adds,
    renames or removes options in the opener.
- `ModelAdmin.get_changeform_initial_data` lets an add form take initial values from GET
  parameters.
- `helpers.py:254` `AdminReadonlyField.get_admin_url` links read-only FK values to the related
  change page.

**We take:**
- **The rules:**
  - ✎/👁 only on a single select, as Django 6.0 decided (#34624); + on any select;
  - no buttons for a related model without frontend pages;
  - the permissions are the related model's own.
- **The href template, updated on `change`.** The placeholder is pk `0` instead of `__fk__`,
  because our detail URLs are `<int:pk>` and `reverse(…, args=["__fk__"])` raises
  `NoReverseMatch`. The project already does this: `lend.html:254` reverses
  `lending:print_sheet` with `0`, and lines 333–334 swap in the pk.
- **GET parameters as initial values** (`get_changeform_initial_data`), limited to the fields
  that carry buttons.

**We leave out:**
- **The wrapper widget.** The admin wraps arbitrary widgets, so it has to delegate `attrs`,
  `choices`, `is_hidden`, `media`, `value_from_datadict`, `id_for_label` and `use_fieldset`. Even
  so it misses `use_required_attribute`, and its `__deepcopy__` aliases the original `attrs`. A
  wrapped select also stops being a `forms.Select`, which breaks every `isinstance` check that
  matters here:
  - `add_bootstrap_classes` (`theme/forms.py:35,39`);
  - crispy's `is_select` (`crispy_forms_field.py:28`);
  - the loop in `dataexchange/forms.py:78`.

  All our target fields already use `TomSelectWidget` or `TomSelectMultipleWidget`. Extending
  those (decision 4) needs none of this.
- **The popup** and everything that serves it: `_popup`, `_source_model`, `popup_response`, and
  `data-model-ref`, which copies new options into other selects of the same model.
- **`_to_field`:** no frontend FK points at a non-pk field. A field with `to_field_name` gets no
  ✎.
- **Delete links:** the frontend has no delete views for these models. If one comes, the admin's
  "no delete on CASCADE" rule applies.

**Why not HTMX here:**
- An endpoint that re-renders ✎ on `change` was the first draft. But the button only depends on
  the selected value. The permissions do not depend on it, so the server learns nothing new.
- The endpoint would also:
  - cost a request per change, including the `hints` context processor's queries;
  - need the page URL for `next`. `request.htmx.current_url_abs_path` returns `None` behind the
    TLS proxy, because the settings have no `SECURE_PROXY_SSL_HEADER`, so the link would silently
    lose its way back.
- The JS needed instead is a few lines in a file we ship anyway, for the unsaved-input guard.

## Decisions taken

1. **Same tab, no popup, no modal** (user, 2026-10-15). A confirm dialog guards unsaved input.
2. **The way back is a URL** (user's proposal, instead of refreshing the options with JS):
   - `?next=` (one local URL since batch 1, as in Django), plus `next_field=<field's HTML name>`
     on add links;
   - the add view returns to `next` with `<field>=<new pk>`.
3. **The form preselects from GET:**
   - only on fields that carry buttons, and only on unbound forms;
   - the pk must be in the field's queryset, otherwise it is ignored;
   - on a multi-select the pk joins the current selection
     (`form.get_initial_for_field`, which also sees `field.initial`, e.g. the licence
     subscribers);
   - the value is validated like any input on save, so a hand-made parameter allows nothing the
     select doesn't offer.
4. **The buttons are part of `TomSelectWidget` and `TomSelectMultipleWidget`:**
   - an optional per-instance `related` attribute, set by the form, like
     `DevicePickerWidget.user`;
   - with it set, the widget renders inside an `input-group` with the buttons (a template that
     includes Django's `select.html`);
   - without it, the output stays exactly as today;
   - the widgets stay `forms.Select`, so `add_bootstrap_classes`, crispy and the TomSelect setup
     in `theme.js` work as before;
   - a select without TomSelect gets no buttons.
5. **`add_related_links(form, request)`** in `theme/related.py` sets `related` on the eligible
   fields and applies the GET preselection. It is a pure function called from the form's
   `__init__` or from the view, like `add_bootstrap_classes`. It applies only to
   `ModelChoiceField` and `ModelMultipleChoiceField`, so the inventory's `ChoiceField` over UUIDs
   is left alone.
6. **A pages registry in `theme`** (`theme/related.py`):
   - the owning apps fill it in `AppConfig.ready()`, keyed by model label (`"core.manufacturer"`);
   - each entry holds the detail URL name and the add URL name;
   - the reason is the same as for `theme.pickers`: the form apps (assets, lending, licenses)
     need the URLs of other apps (rooms, persons), and `theme` must not import them.
7. **The permissions are the related model's default permissions,** which are the ones the target
   views check (`masterdata.py:217-259`, `rooms/views.py:115,135,139`,
   `persons/views.py:71,89,98`):
   - ✎ needs `view_` and `change_`. 👁 needs `view_`. The detail views require `view_`, so the
     admin's "view = view or change" does not carry over;
   - \+ needs `add_`;
   - a user with none of them gets no buttons.
8. **One detail button.** Our detail pages show and edit in one page (`can_change`), so ✎ and 👁
   lead to the same URL.
9. **No tenant links.** A new tenant stays invisible until a group is ticked
   (`PLANS/flexible-tenants.md`), and the tenant page is a settings page that only edits name and
   contact e-mail. The tenant selects stay plain selects.
10. **Icon buttons attached on the right** (user, 2026-10-15). The precedent for TomSelect in an
    `input-group` is the inventory's device select (`inventory/inventorize_room_detail.html:78`).
11. **Pickers stay as they are.** The person, room and device pickers are hidden inputs, not
    selects. Their cards already link to the detail page.
12. **One return parameter, `next`** (user, 2026-10-16): always a local URL, as in Django;
    `?back=` and the query-string `?next=` go (batch 1).

## Plan

### Batch 1: one `next` parameter, a local URL, as in Django

**Findings** (user's review request, 2026-10-16). Two parameters do one job, "return here
afterwards", and the older one uses Django's name for something else:

- **Our `next` is the list's query string, without the path.**
  - Written by 13 links in 10 list templates:
    `{% if request.GET %}?next={{ request.GET.urlencode|urlencode }}{% endif %}`.
  - Read by:
    - `theme/navigation.py` `index_url` and `detail_urls`, used by devices, master data, persons,
      rooms, records and journal;
    - two copies of the same code: `lending/views.py:265-362` and
      `dataexchange/views.py:223-227`.
- **`back` is a local URL.** The inventory search writes it (`inventory/views.py:236` →
  `get_device_state_data(back=…)` → `with_back`). `back_url` in `device_order` and
  `device_transition` reads it.
- **History.**
  - `?next=` came first (lending, d1890e76, 2026-07-13) and spread to every list.
  - `?back=` came with the frontend transitions (e8019e28, 2026-10-14). Their plan gave the reason:
    "`?next=` already carries an index querystring in the frontend, hence `back`."
- **Django:**
  - `next` (`django.contrib.auth.REDIRECT_FIELD_NAME`) is always a local URL: login, logout,
    `set_language`, admin login.
  - `RedirectURLMixin.get_redirect_url(request)` reads it from POST, then GET. It returns the value
    if `url_has_allowed_host_and_scheme` passes, otherwise `""`.
  - `get_success_url()` is `get_redirect_url() or get_default_redirect_url()`.
  - The admin carries its list state as `_changelist_filters` (`get_preserved_filters`), not as
    `next`.
  - So our `next` is the admin's `_changelist_filters` under Django's name, and our `back` is
    Django's `next`.
- **What it costs:**
  - two names for one job, and `next` means two things in one app, right next to the login
    redirect;
  - the query string only leads back to the detail page's own list, because `detail_urls`
    appends it to that list's path. The device teaser is also in the lending list
    (`lending/index.html:42`) and the record list (`records/index.html:73`). A device opened from
    the lending list returns to the *device* list, filtered with the lending list's parameters;
  - three copies of the reading code;
  - the related-links round trip would need both: `back` to the device page, which carries `next`
    itself.

**Steps:**
- `theme/navigation.py`, with Django's names:
  - `get_redirect_url(request)`, the function form of `RedirectURLMixin.get_redirect_url`:
    - reads `next` from POST, then GET;
    - returns it when it is safe, otherwise `""`;
    - one deviation: the value must start with `/`. Without that check, a bookmark's old
      `next=search%3D…` passes as a relative URL and redirects to
      `/assets/devices/12/search=…`, a 404;
  - callers write `get_redirect_url(request) or reverse(…)`, as `get_success_url` does;
  - `with_next(url, redirect_to)` replaces `with_back`;
  - `detail_urls()` returns `(next_url, form_action)`, and `form_action` forwards only a safe
    `next`;
  - `index_url()` and `back_url()` are removed. The module docstring describes the one parameter.
- The 13 list links become `?next={{ request.get_full_path|urlencode }}`, also without filters.
  The origin matters even then, because the teaser sits in three lists.
  - The list fragments are served from the list's own path (`filterbar.html:29`,
    `hx-get="{{ request.path }}"`). So in an HTMX fragment, `get_full_path` is the list URL with
    its filters.
- Readers:
  - records and journal: `get_redirect_url(request) or reverse(…)` instead of `index_url`;
  - lending and the importer page drop their copies. Lending's `form_action`, `edit_url` and
    `return_url` carry the safe `next` next to `flow`;
  - `device_order` and `device_transition`:
    `get_redirect_url(request) or reverse("assets:device_detail", …)`;
  - `get_device_state_data(…, back=)` becomes `redirect_to=`, and the inventory search passes it.
- The context variable `index_url` becomes `next_url` (the name in Django's `set_language`) where
  it holds the way back:
  - the views above;
  - `_detail_base.html`, `devices/detail.html`, `records/detail.html`, `journal/detail.html`,
    `importer_detail.html` and `lend.html`.

  Where it is the list and nothing else, it stays: `masterdata/form.html` (until batch 2),
  tenants, journal cleanup and licence history.
- `_back_link.html` reads "Back" when `request.GET.next` is set, because the link may lead
  somewhere other than its label says ("Back to devices" from the lending list). Without `next`,
  the page's own label stays.
- AGENTS.md, *Architecture*: one line, "a page that returns to its opener reads `?next=<local URL>`
  with `theme.navigation.get_redirect_url`".
- No NEWS line: for the user this is a fix (the device page returns to the list it was opened
  from).
- Tests:
  - update the `?next=search…` tests:
    - `assets/tests/test_masterdata.py:120`;
    - `rooms/tests/test_rooms.py:103`;
    - `lending/tests/test_views.py:382-392`;
  - update the `with_back` users:
    - `inventory/tests/test_inventory.py`;
    - `assets/tests/test_transitions.py`;
    - `theme/tests/test_device_state.py`;
  - a new `theme/tests/test_navigation.py`:
    - POST wins over GET;
    - off-site, `//host` and query-string values give `""`;
    - `detail_urls` forwards only a safe `next`;
  - a device opened from the lending list: the link carries the list URL, Save and Back lead
    there, and Back reads "Back".

### Batch 2: add pages return with the new object

Detail pages already return to `next` (batch 1). Add pages don't yet.

- `theme/navigation.py`: a new `with_next_value(request, pk)` (name tbd):
  - it returns `get_redirect_url(request)` with `<next_field>=<pk>` set, replacing an earlier
    value of that parameter;
  - without a safe `next` it returns `""`, so callers write `… or reverse(…)`;
  - a `next_field` that is not an identifier is ignored.
- Add views:
  - `assets/views/masterdata.py` `_masterdata_add` redirects through the new helper. Cancel goes
    to `next_url = get_redirect_url(request) or reverse(index)`.
  - `rooms/views.py` `room_add` does the same. `rooms/form.html:9,17` hard-codes Cancel, so it
    switches to `next_url`.
- Tests (`assets/tests/test_masterdata.py`, rooms tests):
  - add redirects to `next` with the parameter, replacing an existing one;
  - Cancel leads to `next`;
  - an off-site `next` and a bad `next_field` are ignored.

### Batch 3: the mechanism, the device form and the recover form

- `theme/related.py`:
  - `RelatedPages`, a frozen dataclass with `model`, `detail_url` and `add_url`;
  - `register_related_pages()`;
  - `add_related_links(form, request, *, exclude=())`:
    - origin is `request.get_full_path()`;
    - computes the permissions and sets `widget.related`;
    - applies the preselection.
- `theme/widgets.py`:
  - `TomSelectWidget` and `TomSelectMultipleWidget` render
    `theme/widgets/tom_select.html`;
  - with `related` set, `get_context` adds:
    - the ✎/👁 href for the current value;
    - the href template with pk `0`;
    - the add href, with `next` and `next_field`;
    - the labels;
  - the docstring's "no `template_name`" note is updated; the "no `Media`" one stays.
- `theme/templates/theme/widgets/tom_select.html`:
  - plain `{% include "django/forms/widgets/select.html" %}` without `related`;
  - with it, the `input-group` and the buttons, carrying `data-related-link`,
    `data-href-template`, `data-confirm` and the select's id.
- `theme/assets/js/related-links.js`, imported by `theme.js`, holds two delegated listeners and
  needs no setup, so forms swapped in by HTMX work as well:
  - **`change`** on a select with buttons:
    - replaces `/0/` in the template's path, never in its query;
    - sets the ✎ href, or removes it and sets `aria-disabled` when the select is empty.
  - **`click`** on `[data-related-link]`:
    - the form is dirty if its entries differ from a snapshot taken at the first `focusin`
      inside it; this is the approach of the lend page's own check (`lend.html:346-372`);
    - files compare by name and size;
    - a dirty form gets `confirm(link.dataset.confirm)`, with the string translated in the
      template.
- Registrations:
  - `assets/apps.py` `ready()`: device type, manufacturer and supplier;
  - a new `ready()` in `rooms/apps.py`: room.
- Forms:
  - `DeviceForm.__init__` calls `add_related_links(self, request)`. This covers device type,
    manufacturer and supplier; tenant is a plain select (decision 9);
  - `RecoverForm.room`: the call goes in `device_transition`. Its form posts to its own URL
    (`transition.html:24`), so its existing `?next=` and the new `room=` both survive.
- `assets/devices/includes/_form_fields.html`: the collapsed *Procurement* section also opens when
  `request.GET.supplier` is set, so the preselected supplier is visible.
- Docs:
  - one NEWS line: form selects of master data, rooms and persons get buttons to open the
    selected entry or add a new one, and both lead back to the form;
  - one paragraph in `docs/guides/devices.md`, *Geräte-Detailseite*.
- Tests (`theme/tests/test_related.py`, `assets/tests/test_devices.py`,
  `assets/tests/test_transitions.py`):
  - without `related`, `TomSelectWidget` renders exactly as before;
  - permissions none / view / view+change / add give no buttons, 👁, ✎ and +;
  - a multi-select gets + only; a plain select, a picker, an unregistered model and a
    non-model field are untouched;
  - preselection:
    - `?manufacturer=<pk>` preselects on the add page and on the detail page;
    - it is ignored on POST;
    - a pk outside the queryset, or one that isn't a number, is ignored;
  - the recover form's round trip keeps the inventory's `next`;
  - a contract test over the registry: every registered URL name reverses, and its view answers
    403 without and 200 with exactly the derived permission.
- Screenshot check (`/verify`): light and dark, `col-md-4` width, invalid state, nothing selected,
  the collapsed section opened by a preselection.

### Batch 4: lending

- `LendingForm.room`:
  - `lend.html` renders `{{ form.room }}` by hand; the widget brings its buttons along;
  - the inline JS finds the select by id (`lend.html:303`), and the id stays the same.
- **Buttons only in record mode** (`/lending/<pk>/`):
  - in the picker flow (`/lending/lend/`) the device and person exist only in the browser; the
    view reads the device from POST (`lending/views.py:327-337`), so both would be lost;
  - picking the device again overwrites the room with the device's location
    (`lend.html:322-331`).
  - The call in `lend` passes `exclude=("room",)` in the picker flow.
- Tests: the buttons appear in record mode and not in the picker flow; the round trip keeps the
  lending's `?next=`.

### Batch 5: licences and persons

- The person registration: a new `ready()` in `persons/apps.py`.
- `persons/views.py` `person_add`: redirect and Cancel as in batch 2. `persons/form.html:9,17`
  hard-codes Cancel.
- `LicenseForm`:
  - crispy's `FloatingField` cannot hold an `input-group`, because the label has to follow the
    control inside `.form-floating`;
  - so `manufacturer`, `supplier` and `device_type` get `TomSelectWidget` and move out of
    `FloatingField`, like on the device form;
  - `subscribers` gets + (persons) only, because it is a multi-select;
  - a new person without an e-mail address is not in its queryset (`licenses/forms.py:49`), so
    the preselection ignores it (decision 3).
- `licenses:new` answers only HTMX requests (`NotImplementedError` otherwise), so the way back
  would land on the licence list instead of the form. See open question 1.

## Progress

- [x] **0. This document**
- [x] **1. One `next` parameter, a local URL, as in Django**
- [ ] **2. Add pages return with the new object**
- [ ] **3. The mechanism, the device form and the recover form**
- [ ] **4. Lending**
- [ ] **5. Licences and persons** (open question 1)

## Open questions

1. **New licence (batch 5):** `licenses:new` exists only as an HTMX fragment. The options:
   - (a) give it a full page, like `edit`; `licenses/form.html` already exists;
   - (b) buttons only on the edit form.

   Recommendation: (a).

## Alternatives considered and rejected

| Approach | Why not |
|---|---|
| Subclass `RelatedFieldWidgetWrapper` | `get_context` and `get_related_url` hold admin URL names and popup parameters. Overriding them leaves only the delegation methods, and the frontend would import `django.contrib.admin` while the admin is phased out. |
| Our own wrapper widget | The delegation is fragile, and the wrapper breaks the `isinstance` checks of `add_bootstrap_classes`, crispy and `dataexchange/forms.py` (see *What we take from the Django admin*). |
| Admin popup or Bootstrap modal | Not wanted (user). A modal would also need the add views to answer as fragments, and JS to add the option to TomSelect. |
| New tab, refreshing the options when the form tab is visible again | Keeps unsaved input, but needs JS that refetches the page and merges options into TomSelect. The user preferred the URL round trip (decision 2). |
| HTMX endpoint that re-renders ✎ on `change` | See *Why not HTMX here*. |
| Extending `theme/includes/_field.html` | Misses fields rendered by hand (`lend.html`) or by crispy (licences), and needs context per field. |
| `get_absolute_url` on the models | Per-screen URLs don't belong in core models (AGENTS.md), and it has no add counterpart. |
| Keep `?next=<query string>` and `?back=<URL>` side by side | Two names for one job, `next` means two things in one app, and the query string only leads back to one list (batch 1). |
| Rename our `next` to the admin's `_changelist_filters` | The name is honest, but we still have two parameters, and the detail page still only returns to its own list. |

## Open follow-ups

- **Read-only pages link related objects,** like the admin's read-only fields
  (`AdminReadonlyField.get_admin_url`). The device detail page without the change permission shows
  manufacturer, device type and supplier as plain text (`devices/detail.html:24-26, 58-61`), and
  so does the device list. The registry already knows where they lead and who may open them.
- **A + in the person picker** (`_picker.html`), for contact person and borrower.
- **Organisational units and smallstuff things** have no frontend pages
  (`PersonForm.organizational_unit`, `AssignedThingsForm.thing`). Once they do, registering them
  is enough.
- **`lend.html`'s own unsaved-input check** (`lend.html:346-372`) could move onto the shared one.
- **Delete links,** if delete views come. Then the admin's rule applies: no delete link when the
  FK's `on_delete` is CASCADE.
- **Every link that opens a detail page passes `next`.** This covers the dashboard search, the
  related lists on the room and person pages, and the device page's state-change links, so that
  a state change returns to the device page with its own `next`.

## Pitfalls

- **Widget templates have no `perms` and no `request`,** because no context processors run.
  `add_related_links` computes everything from `request` and stores it on the widget, like
  `DevicePickerWidget.user`.
- **`next` has to survive the POST:**
  - detail pages carry it in `form_action`;
  - add pages post to their own URL (`<form method="post">` without `action`), which keeps the
    query string;
  - a template that sets `action` must add `next` itself, or carry a hidden
    `<input name="next">`, since `get_redirect_url` reads POST first.
- **Old URLs:** a stale `?next=search%3D…` falls back to the list, because of the leading-`/`
  check. An old `?back=` is ignored.
- **Nested `next`:** the round trip puts a URL that carries `next` into `next`, which shows up as
  `%253F` in the address bar. Build it with `urlencode` or `|urlencode`, never by concatenation.
- **`get_full_path` in HTMX fragments:** it is only right because the list fragments are served
  from the list's own path. A fragment served from another URL has to pass the page URL itself.
- **Forms rendered as HTMX fragments** would get the fragment's URL as their origin. Don't use
  `request.htmx.current_url_abs_path` instead: it is `None` behind the TLS proxy. Forms with
  buttons are full pages (open question 1 makes the new-licence form one).
- **The pk placeholder:** the template is the detail URL reversed with `0`. JS replaces `/0/` in
  the path only, because `next` in the query is URL-encoded and could contain other text.
- **The dirty check compares form entries, not `defaultValue`:**
  - pickers write hidden inputs, and a hidden input's `defaultValue` follows its `value`;
  - the snapshot is taken at the first `focusin`, after load-time scripts such as TomSelect and
    the glue in `lend.html` have run;
  - `URLSearchParams(FormData)` would turn every file into `"[object File]"`.
- **The round trip keeps one field.** All other unsaved input is gone (decision 1, guarded by the
  dialog). The preselected value is not stored until the form is saved; the message on return
  says what was created, not that the device was changed.
- **Collapsed sections hide a preselected value** (the device's *Procurement*); open them as in
  batch 3.
- **Soft-deleted related objects:** if a device's device type is soft-deleted, the select renders
  empty because the queryset excludes it, and ✎/👁 is disabled, as in the admin.
- **TomSelect inside an `input-group`:** `tom-select.bootstrap5` styles it. Don't put it in an
  `overflow: hidden` box, or the dropdown gets clipped.
- **Translations:** button titles use `blocktranslate` with the model's `verbose_name`, which is
  lazy-translated since the visual polish. Don't run `makemessages`.

## Decided during implementation

Nothing yet.
