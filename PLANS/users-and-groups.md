<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# Users and groups in the frontend

**Status:** batch 0, the plan; nothing built yet. Started 2026-11-20.

## Why

- **The problem:** after a deployment, operators must turn 230 Django permissions into working groups. About 80 of them mean something in DLCDB, and their names don't say what they unlock: "Core | lent record | Can view lent record" is the *Lending* menu.
- **Today:** users, groups and permissions exist only in the Django admin, which is being phased out (`PLANS/admin-to-frontend.md` › *Users and groups*).
- **The goal:** *the* manager for groups (permissions, tenants, members) and users, in the frontend. Setting up a fresh installation is one path through it.
- **The principle:** the app explains itself, so the docs drop what it shows. A permission listed by hand in the docs drifts from the code and has operators copy codenames into the admin: two sources of error.
- **A first attempt was dropped:** a one-off "Helpdesk role" page with a fixed group name, a new concept ("role") and no members.

## Decisions

### Which permissions are DLCDB's own

- **The code marks them by checking them.** A permission counts as DLCDB's own if one of these names it:
  - the view decorator `htmx_permission_required` (every frontend view; it records the permissions it is given);
  - a menu entry's `required_permission`;
  - a lifecycle `Transition.permission`.

  That is 67 permissions today, collected without a list.
- **The gap: about 12 *change* permissions** that a page which edits in place checks inside its body. They each get one line in a short list:
  - `core.change_person`;
  - the four settings pages: Branding, lending, licences, HR sync;
  - the manufacturer, supplier and device type pages;
  - units and positions;
  - `lending.change_lendingprofile`;
  - `dataexchange.change_importerlist`.

  A guard test fails, naming the permission, when the code checks one that is neither collected nor listed.
- **Not a codename prefix:** Django's view/add/change/delete names are fixed. `has_perm`, the admin and DRF use them, and renaming them would need a migration of every group's grants. DLCDB's own permissions already carry one (`transition_…`).
- **Not a hand-written list of about 80 entries** with hand-written labels: every new permission would need an entry.
- **Labels are derived:**
  - model name and action ("Person · change");
  - the lifecycle's labels for transitions; lend and return share one permission;
  - the menu entry for `can_inventorize`.

  Help lines come from menu entry descriptions where there is one. Django's `Permission.name` (English, stored in the database) is never shown.
- **Change requires view:** derived. Ticking add, change or delete also grants the model's view permission, when that is DLCDB's own.
- **Sensitive permissions are a short explicit list in `accounts`**, each with its warning shown as its help line:
  - `accounts.change_group`, `accounts.change_customuser`;
  - `tenants.change_tenant`: sees every tenant;
  - `lending.add/change_lendingprofile`: slip templates read everything a lending reaches;
  - `dataexchange.change_udbsyncconfiguration`;
  - restore, recover.
- **Admin-only permissions** (for example `core.view_note`) are collected through their menu entries like any other. Without the Staff flag the menu hides admin entries anyway. They get no special marking.

### Group profiles

- **What they are:** a *group profile* (Gruppenprofil) is a named list of permissions that DLCDB ships; "profile" alone is taken by lending profiles.
- **Copy only:** applying a profile adds its permissions to the group, and the group doesn't remember it. The UI says "New group from the profile *Daily work*" or "Add the permissions of a profile", never "Profile: …" on a group. After an update, applying it again adds new permissions. No model, no migration.
- **First profiles**, in `accounts` (a test checks every name exists):
  - **Daily work:**
    - `core.view/add/change_device`, `core.view_lentrecord`;
    - transitions: order, locate, relocate, lend, lose, find (no decommissioning);
    - `core.view/add/change_licencerecord`, `_person`, `_room`, `_manufacturer`, `_supplier`, `_devicetype`;
    - `core.view_record`;
    - `smallstuff.view/add/change_assignedthing`;
    - `core.can_inventorize`, `dataexchange.view_importerlist`.
  - **Administration:**
    - `organization.view/change_branding`;
    - `core.view/add/change/delete_organizationalunit` and `_organizationalposition`;
    - `lending.view/change_lendingconfiguration`, `lending.view/add/change/delete_lendingprofile`;
    - `licenses.view/change_licensesconfiguration`;
    - `dataexchange.view/change_udbsyncconfiguration`, `dataexchange.view_udbsyncrun`;
    - `tenants.view/add/change/delete_tenant`;
    - `journal.view/delete_journalentry`.

    Not users and groups.

### Screens and rules

- **Order:** groups first (batches 1–4), then users (5–6).
- **Widgets:**
  - **Permissions:** checkboxes grouped by model, each with its help line, no JS.
  - **Members:** the dual-pane `filtered-select-multiple-widget` (the user's npm package, bundled by esbuild; it needs no new features for this).
- **Staff and Superuser flags** are not set in the frontend: only badges. They stay with the admin, LDAP and `createsuperuser`.
- **Direct per-user permissions** (`user_permissions`) are ignored by the frontend.
- **History:** one journal entry per save, naming what changed (permissions added and removed, members, deactivation), never passwords. Not simple-history.
- **Passwords:** the administrator sets an initial one on *New user*, or none for LDAP accounts, and can set a new one on the user page. No reset mail.
- **The admin's user and group screens stay registered**, like the settings and tenant admins. The menus link the frontend; Settings › More reaches the admin, for example for the flags.
- **Permissions:**
  - group pages: `accounts.view_group`; editing: `change_group`; *New group*: `add_group`; deleting: `delete_group`;
  - members and the user pages: `accounts.view/change/add_customuser`;
  - the tenants card: `tenants.change_tenant`.

### Docs: only what the app can't show

- **The app is the only reference for permissions.** No permission list stays in the docs, not even a generated one.
- **A warning in the docs becomes behaviour, or a note where someone acts:**
  - guards against locking oneself out;
  - LDAP members read-only, with the reason;
  - the tenants card says permissions apply in all of a user's tenants;
  - superusers learn they see devices only through their groups.
- **`berechtigungen.md` becomes a short concept page:** users, groups and tenants, plus LDAP briefly.
  - **Gone:** the permission families and their notes, the Navigation table, the permission columns of *Statuswechsel* (the lifecycle stays in `konzept.md`), the paragraphs on settings permissions, and *Beispiel-Gruppen*.
  - **Moved onto the tenant pages:** the tenant warnings and the list of what isn't tenant-scoped.
  - **The *Django-Admin* section** shrinks with every module that moves.
- **`erste_schritte.md` stays as a short checklist:** one line per step, each linking to its screen. The existing hints (no tenant, no rooms, no external or auto-return room, no contact email) guide the details; the "no tenant" hint links to *New group*.
- **`setup.md`:** after `createsuperuser`, one sentence: log in and follow *Erste Schritte*.

## Turned down

- **Default groups by migration or `post_migrate`** (Wagtail): forced onto existing installations.
- **A management command:** the setup belongs in the frontend.
- **A one-off "Helpdesk role" page:** see Why.
- **All 230 permissions with a search, as in the admin.**
- **Object permissions** (django-guardian, rules): groups and tenants cover the need.
- **The dual-pane widget for permissions:** its panes are native selects, so help lines could only be hover tooltips.

## Pitfalls

- **Hidden permissions:** groups hold permissions that aren't DLCDB's own (per-model CRUD nobody checks, the dead `dlcdb` app label). The form keeps them on save and lists them read-only.
- **The decorator's record is complete only once every view is imported:** the collector loads the URLconf first (`get_resolver().url_patterns`). It lives in `core.utils.htmx`, since core imports no other app.
- **Look permissions up by app label and codename together:** there are proxy models (`lentrecord`, `licencerecord`, `accounts.Group` beside `auth.Group`) and the legacy `dlcdb` app label, which repeats codenames.
- **Escalation:** whoever has `accounts.change_group` can grant themselves anything shown. Same as the admin today; the sensitive list says so.
- **Locking oneself out:**
  - no deactivating oneself;
  - no removing `change_group` from one's last group that has it;
  - no leaving that group.
- **LDAP:**
  - membership of mirrored groups and every flag are overwritten at each login;
  - users and mirrored groups appear at the first login, so *New group* must accept the exact LDAP name in advance;
  - `AUTH_LDAP_MIRROR_GROUPS` may also be `True` (all groups mirrored).
- **Superusers see devices only through their groups** (DECISIONS: no superuser exception). *New group* suggests adding oneself.
- **`has_perm` caches per user object:** after changing a group, fetch the user again (as `conftest.make_user` notes).
- **Deleting a group:** members lose access; an LDAP-mirrored group returns at the next login; `Group` has no soft delete.
- **The dual-pane widget:** check dark mode and phone width (its open issues #1 and #2).

## Open follow-ups

- **The admin's user form lets anyone with `change_customuser` tick *Superuser*.** Make the flags and `user_permissions` read-only there for non-superusers.
- **Direct per-user permissions** stay invisible in the frontend. Show or migrate them if they turn up in practice.
- **Reset links by mail**, and a password change page in DLCDB's own look for the account menu: today's `accounts/password_change/` renders the admin's look.

## Progress

- [x] **0.** This plan; the first attempt discarded.
- [ ] **1. Which permissions are DLCDB's own.**
  - The decorator records its permissions.
  - The collector: decorator, menus, lifecycle, the ~12 extra lines.
  - Derived labels and the view requirement; the sensitive list.
  - The guard test.
- [ ] **2. Groups, read-only.**
  - Groups list (members, tenants, LDAP badge) and group page: permissions by model with labels, tenants, members, other permissions read-only.
  - The menu entry *Groups and permissions* opens the frontend.
- [ ] **3. Editing a group:**
  - permissions (keeping hidden ones, view added, the lock-out guard);
  - tenants card (reusing `tenants.views.toggle`);
  - members (dual-pane widget; LDAP read-only);
  - journal entries.
- [ ] **4. Group profiles:**
  - *Daily work* and *Administration*;
  - *New group* (name, profile, optional tenant, members), *Add the permissions of a profile*, deleting a group;
  - the "no tenant" hint links to *New group*.
- [ ] **5. Users, read-only and deactivating:**
  - users list (email, name, active, last login, groups, badges) and user page (groups, what the user may do, tenants seen);
  - deactivate and reactivate (not oneself); journal entries;
  - the menu entry *Users* opens the frontend.
- [ ] **6. New user and passwords:** email, name, initial password or none; groups; set a new password on the user page.
- [ ] **7. Wrap-up:**
  - docs per *Docs: only what the app can't show*;
  - NEWS;
  - this plan retires into DECISIONS.md, `PLANS/admin-to-frontend.md` › *Users and groups* ticked.

Each batch also trims the doc passages it makes obsolete.
