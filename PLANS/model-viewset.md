<!--
SPDX-FileCopyrightText: Thomas Breitner

SPDX-License-Identifier: CC0-1.0
-->

# ModelViewSet: reusable list, add, edit and delete pages

**Status:** batch 1 done (the viewset and the smallstuff catalogue); next: batch 2, units and positions. Started 2026-11-23.

## Why

- **The problem:** the same list/add/edit/delete flow exists three times, each written by hand: device types, manufacturers and suppliers (`assets/views/masterdata.py`, `MasterdataSpec`), units and positions (`organization/views_masterdata.py`, `Kind`), lending profiles (`lending/views_profiles.py`). The smallstuff catalogue (`smallstuff.Thing`) would be the fourth copy; today it is only in the Django admin (`PLANS/admin-to-frontend.md`).
- **The goal:** one small reusable component for these pages, like the Django admin offers them out of the box, without re-implementing the admin. Users then know one list, one form and one delete page.
- **Start small:** smallstuff things first, then units and positions.

## Decisions

- **`theme.viewsets.ModelViewSet`, after Wagtail's `ModelViewSet`** (https://docs.wagtail.org/en/stable/reference/viewsets.html#modelviewset): its names and structure, so Django developers recognise them.
  - One view class per page, set on the viewset: `index_view_class`, `add_view_class`, `edit_view_class`, `delete_view_class`. They subclass Django's `ListView`, `CreateView`, `UpdateView` and `DeleteView`; a model changes a page by subclassing its view (`get_context_data`) and setting `*_template_name`.
  - The viewset's attributes: `model`, `form_class` (`get_form_class()`), `list_display` (field names or `Column`), `search_fields`, `ordering`, `list_per_page`, `icon`, `url_namespace` (defaults to the model name).
  - *Decided in batch 1:* no `form_fields` yet: every form so far has its own rules (similar names, help texts). No `get_url_name()` on the viewset: it doesn't know the app namespace it is included in, so the views build their sibling URL names from `request.resolver_match.namespace`.
  - `get_urlpatterns()` and `urls`: the URL names `index`, `add`, `edit`, `delete` in the viewset's own namespace, nested in the app's (`smallstuff:thing:edit`); the app's `urls.py` includes them.
  - Each view is wrapped in `htmx_permission_required` with the model's view, add or delete permission, so the group pages collect them; the edit page checks the change permission itself (`CHECKED_IN_VIEWS`).
  - What the project already has stays: the filterbar, pagination, the similar-names check, `?next=`, `linked_message` and the existing message wording.
- **Every viewset has its own index page**, units and positions too: one interface users already know.
- **A protected object can't be deleted:** the delete page asks Django's deletion `Collector` whether a `PROTECT` relation keeps it, and then says so instead of offering to delete.
- **Things:** `AssignedThing.thing` is `PROTECT`, so a thing that was ever handed out can't be deleted, only renamed; deleting would have taken its history along (`CASCADE`). The slug stays and `Thing.clean()` fills it from the name. The thing's page lists who holds it now.
- **smallstuff has no settings model:** the catalogue is its only configuration, under *Settings › Smallstuff catalogue*.

## Turned down

- **A second Django `AdminSite` with our own templates:** its templates expect the admin's `AdminForm` and `ChangeList`, its JavaScript and `_changelist_filters` instead of `?next=`; it would be the admin again.
- **A spec dataclass with the per-model differences as lambdas**, like `MasterdataSpec` and `Kind`: methods and view subclasses read better.
- **Helpers from `django.contrib.admin.utils`** (`label_for_field`, `NestedObjects`): undocumented internals; Django's `Collector` and a small `Column` do.
- **Menu entries as viewset attributes** (Wagtail's `menu_label`, `add_to_settings_menu`): each app's `navigation.py` declares them, as for every other page.
- **The names `ModelPages` and `CrudAdmin`:** "pages" sounds like a CMS, "Admin" like the Django admin being phased out.

## Pitfalls

- Two names can give the same slug ("Maus!" and "Maus?"): `Thing.clean()` refuses the second, since a ModelForm doesn't check unique fields it doesn't show.
- `PROTECT` also blocks deleting a thing in the admin, which then shows its "protected" page.
- The nested namespace (`smallstuff:thing`) is no app label: `nav_focus` looks up the app by its first part.

## Open questions

- **Batch 2: a list embedded in a card via HTMX?** The list is already a partial, but a card needs it without `hx-push-url` and the filterbar, and its links need an explicit `next` (`request.htmx.current_url_abs_path` is None behind the proxy). Proposal: own pages now, embed only when a page needs a list inline.

## Open follow-ups

- A usage view and a history view per viewset, as in Wagtail.
- Correcting or deleting a single smallstuff assignment: still the admin.
- Device master data and lending profiles on the viewset.

## Progress

- [x] **0.** This plan.
- [x] **1. The viewset and the smallstuff catalogue:**
  - `theme/viewsets.py` and `theme/templates/theme/viewsets/`;
  - `ThingViewSet`: index with the number issued, add, edit with the current holders, delete; `PROTECT` and the slug from the name (migration);
  - *Settings › Smallstuff catalogue* opens it, without the Staff flag; the *Administration* group profile gets the thing permissions;
  - `docs/guides/kleinkram.md`, NEWS; `PLANS/admin-to-frontend.md` › *Smallstuff catalogue* ticked.
- [ ] **2. Units and positions as viewsets:**
  - their own index pages and settings entries; `organization/views_masterdata.py` and `organization/name_*.html` go;
  - the DECISIONS bullet "Units and positions live on Settings › Organization as cards" is replaced; the embedding question settled.
- [ ] **3. Wrap-up:** this plan retires into DECISIONS.md.
