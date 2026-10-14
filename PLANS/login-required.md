<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Login required by default

**Status:** implemented (batches 1–4, 2026-10-14): the middleware makes login the default, the
per-view login decorators are gone, every 403 names the missing permission, and the API schema
needs authentication. What is left is under *Open follow-ups*.

## Why

Almost everything in DLCDB requires at least a login, but every view guards itself
(`htmx_login_required`, `htmx_permission_required`, `permission_required(raise_exception=True)`,
mixins). An audit of every resolved URL (2026-10-14) found no unguarded project view. Django's
`LoginRequiredMiddleware` (5.1+) makes login the default, so a view added later without a
decorator is still login-only. After this work, one place decides "logged in?", and the view
decorators only express permissions.

Anonymous users get two different answers today. About 17 views redirect them to the login
page; the permission-gated views answer with a 403 page that carries a log-in link. The 403 page
names the missing permission only for `htmx_permission_required`.

## Decisions taken

1. **Anonymous requests are redirected to the login page with `?next=`, everywhere.** HTMX
   requests get `HX-Refresh`: the browser reloads the page, and that full request gets the
   redirect, with `next` pointing at the page rather than at the fragment. This replaces the 403
   that anonymous users got from permission-gated views.
2. **`dlcdb.accounts.middleware.LoginRequiredMiddleware`** subclasses Django's middleware and
   overrides `handle_no_permission` for HTMX. It lives in `accounts`, the app that owns login.
3. **Public views are marked with `login_not_required`:** `favicon`, `set_language` (the
   language switcher shows on the login page) and the `admin/login/` redirect. The auth views, the
   admin login, the debug toolbar and DRF views exempt themselves. A test pins this allowlist.
4. **The per-view login decorators go** (`htmx_login_required`, plain `login_required`). The
   middleware runs before every view decorator and answers the same way, so they can no longer
   fire.
5. **Every 403 names the missing permission.** All permission guards in the frontend apps use
   `htmx_permission_required`. Inline checks raise `PermissionDenied` with the same message. The
   403 page shows the Branding IT address, like the login page.
6. **The OpenAPI schema and Swagger UI require authentication**
   (`SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"]`). The middleware cannot cover them because DRF
   views opt out of it. The API itself is guarded by DRF's `IsAuthenticated`. The Swagger UI is a
   browser page, so it also carries Django's `login_required`: anonymous visitors are sent to the
   login page instead of a 403 page that has no log-in link since batch 1.

## Alternatives considered and rejected

- **Extending django-htmx's `HtmxMiddleware`.** It only sets `request.htmx`, offers no hook to
  extend, and never sees the resolved view, so it cannot read `login_not_required`.
- **A per-view check returning `HX-Redirect` to `LOGIN_URL`**
  ([djangotricks](https://www.djangotricks.com/tricks/nEgWAaGGd9ZG/)). This is the per-view
  pattern `htmx_login_required` already follows, the opposite of a central default. It also
  drops `next`.
- **Keeping the 403 for anonymous users.** It would turn the ~17 redirecting views into 403s as
  well, and lose `next`.

## Open follow-ups

### Media files

Planned in `PLANS/protected-media.md`.

Apache serves `/media/` with `Require all granted` (`docs/betrieb/setup.md`). That includes
attachments, HR person images and SAP comparison results. Django middleware never sees these
requests. Protecting them needs a Django view with `X-Sendfile`, or an Apache-level rule.

## Pitfalls

- **`handle_no_permission` is not in Django's documentation**, which lists only `get_login_url`
  and `get_redirect_field_name` as hooks. It exists unchanged from 5.1 to 6.1. The HTMX test pins
  the behaviour, so an upstream change fails the suite.
- **A new public view needs `login_not_required`** and an entry in the allowlist test.
- **`htmx_permission_required` means "any of"**, Django's `permission_required` means "all of".
  Every current use passes a single permission.
- **The admin keeps its own guards and bare 403s.** It is being phased out.
- **Codenames repeat across apps:** the `accounts.Group` proxy gives `accounts.*_group` beside
  `auth.*_group`. `missing_permission_message` looks permissions up by app label and codename.
- **A UDB-synced person is refused without a permission name.** The user may hold
  `core.change_person`; the person is read-only because the HR sync manages it.
- **Permission names are mixed-language:** the model part is translated, but the permission name
  is stored in English at migrate time, as the group admin shows it.
- **Admin views carry `login_url = admin:login`**, so the middleware sends anonymous admin
  requests to `/admin/login/?next=…`. The project's redirect from there to `/accounts/login/`
  needs `query_string=True`, or `next` is lost (it was lost before batch 1 too).

## Batches

### 1. Middleware, public exemptions

- `dlcdb/accounts/middleware.py`; `MIDDLEWARE` after `HtmxMiddleware`.
- `login_not_required` on `favicon`, `set_language` and the `admin/login/` redirect
  (`dlcdb/urls.py`, `dlcdb/organization/views.py`); the redirect keeps the query string.
- `403.html`: drop the "If you are not logged in" block. Anonymous users can no longer reach the
  page; CSRF failures use `403_csrf.html`.
- Tests:
  - the four `test_anonymous_is_refused` tests expect the login redirect and become
    `test_anonymous_is_sent_to_the_login`;
  - `accounts/tests/test_login_required.py`:
    - a view guarded only by a permission redirects to login, or refreshes over HTMX;
    - `set_language` and `favicon` work anonymously;
    - the admin keeps `next` through its login redirect;
    - the public URL allowlist.
- NEWS.

### 2. Drop the now-dead login decorators

- Delete `htmx_login_required`.
- Remove its uses and plain `@login_required` from:
  - `dashboard`, `theme`, `lending`, `inventory`, `licenses`, `notifications`;
  - `assets/views/devices.py`, `assets/views/relocate.py`.
- Reword the docstrings that cite it.
- The existing anonymous and `HX-Refresh` tests stay unchanged and now cover the middleware.

### 3. Every 403 names the missing permission

- `core/utils/htmx.py`: `missing_permission_message(*perms)` becomes public. Its message
  becomes translatable (`ngettext`) and it looks the permission up by app label and codename.
- Django's `permission_required(…, raise_exception=True)` becomes `htmx_permission_required(…)`
  (51 call sites in 14 files).
- The 4 `PermissionRequiredMixin` views use `method_decorator(htmx_permission_required(…))`.
- The inline `raise PermissionDenied` checks in the frontend views and the device picker pass the
  message.
- `403.html`: contact address `branding.organization_it_dept_email|default:DEFAULT_FROM_EMAIL`.
- Tests:
  - the 403 page names the permission, for a decorator and for an inline check;
  - the HTMX flash message names it too;
  - the 403 page shows the Branding IT address;
  - the tenant matrix toggle over HTMX without the change permission refreshes instead of a 403.

### 4. API schema requires authentication

- `SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"]`; `login_required` on the Swagger UI URL.
- One sentence in `docs/betrieb/api.md`.
- Tests in `api/tests/test_schema.py`:
  - schema: refused when anonymous, 200 with a token or a session;
  - Swagger UI: login redirect when anonymous, 200 when logged in.
- NEWS.

## Progress

- [x] **0. This document**
- [x] **1. Middleware, public exemptions**
- [x] **2. Drop the now-dead login decorators**
- [x] **3. Every 403 names the missing permission**
- [x] **4. API schema requires authentication**
