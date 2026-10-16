# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Duplicate check for the add pages: does the new entry already exist under
another spelling?

The name typed on an add page is compared with every existing entry,
deactivated ones too, after normalizing both (``words``): case, umlauts and
accents, punctuation and noise words such as "GmbH" do not count.

- Identical after that ("pro-com" and "Procom"): the add page refuses, and
  offers the existing entry instead.
- Similar (a typo: a ``difflib`` ratio of at least ``SIMILARITY``; or all words
  of one name among the other's: "Pulse" and "Pulse Secure"): the add page
  warns, and saves once the user ticks "Create anyway" for exactly the entries
  listed.

A form declares what to compare as ``similar_names`` and calls
``check_similar_names(self)`` from its ``clean()``; the add view renders the
result with ``similar_context`` and ``theme/includes/_similar.html``.

Compared in Python, not with ``iexact``: SQLite folds the case of ASCII letters
only. The tables are small (hundreds of rows), so every check reads them all.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass

from django.urls import reverse
from django.utils.translation import gettext as _

from .navigation import get_redirect_url_after_add
from .related import get_related_pages

# Words that tell nothing apart in a company name: "Dell Inc." is "Dell".
COMPANY_NOISE_WORDS = frozenset(
    {"ag", "bv", "co", "corp", "corporation", "gmbh", "group", "inc", "kg", "llc", "ltd", "plc", "sa", "se"}
)

# From this difflib ratio on, two names count as similar: about one typo in a
# short name ("Lenvoo" and "Lenovo").
SIMILARITY = 0.8

# The most entries the add page lists, best first.
MAX_MATCHES = 5

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})


@dataclass(frozen=True)
class SimilarNames:
    """What an add form compares with the existing entries of its model."""

    fields: tuple[str, ...]
    noise_words: frozenset[str] = frozenset()
    # False: identical names only, for names whose neighbours look alike by
    # nature (room F1.01 next to F1.02).
    fuzzy: bool = True


@dataclass(frozen=True)
class Matches:
    """The existing entries a new one may duplicate: identical and similar ones, best first."""

    identical: list
    similar: list

    def __bool__(self):
        return bool(self.identical or self.similar)


def words(text, noise_words=frozenset()):
    """
    The words of ``text`` that count in a comparison: case-folded (ß → ss),
    ä/ö/ü → ae/oe/ue, other accents dropped, without punctuation and without
    ``noise_words``.
    """
    text = unicodedata.normalize("NFC", text).casefold().translate(_UMLAUTS)
    text = "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))
    return [word for word in re.findall(r"[^\W_]+", text) if word not in noise_words]


def find_similar(model, similar_names, values):
    """
    The entries of ``model``, deactivated ones too, whose name is identical or
    similar to ``values``, a dict of the compared fields' typed values.
    """
    new_words = _name_words(values, similar_names)
    if not new_words:
        return Matches([], [])
    new_name, new_word_set = "".join(new_words), set(new_words)

    # One sequence against many: difflib caches the second one.
    matcher = difflib.SequenceMatcher(autojunk=False)
    matcher.set_seq2(new_name)

    identical, similar = [], []
    manager = getattr(model, "with_softdeleted_objects", model._default_manager)
    for obj in manager.all():
        existing_words = _name_words({name: getattr(obj, name) for name in similar_names.fields}, similar_names)
        existing_name = "".join(existing_words)
        if not existing_name:
            continue
        if existing_name == new_name:
            identical.append(obj)
            continue
        if not similar_names.fuzzy:
            continue
        matcher.set_seq1(existing_name)
        existing_word_set = set(existing_words)
        contained = new_word_set <= existing_word_set or existing_word_set <= new_word_set
        # The quick ratios are upper bounds of the real one, as in difflib.get_close_matches.
        if contained or (matcher.real_quick_ratio() >= SIMILARITY and matcher.quick_ratio() >= SIMILARITY):
            ratio = matcher.ratio()
            if contained or ratio >= SIMILARITY:
                similar.append((ratio, obj))

    similar.sort(key=lambda match: match[0], reverse=True)
    return Matches(identical[:MAX_MATCHES], [obj for _ratio, obj in similar[:MAX_MATCHES]])


def check_similar_names(form):
    """
    From a form's ``clean()``: refuse a new entry with the name of an existing
    one, and one with a similar name unless the user ticked "Create anyway" for
    the entries listed. Editing an entry is not checked.

    The error goes on the first compared field. A field with an error makes
    Django skip its own unique checks of that field, and with them their
    technical "Constraint … is violated" message.

    The matches stay on the form as ``similar_matches``, for ``similar_context``.
    """
    form.similar_matches = Matches([], [])
    similar_names = form.similar_names
    # A field that failed already would leave half a name: "Max" alone is
    # similar to every Max.
    if form.instance.pk is not None or any(name in form.errors for name in similar_names.fields):
        return
    model = form._meta.model
    form.similar_matches = matches = find_similar(model, similar_names, form.cleaned_data)
    field_name = similar_names.fields[0]

    if matches.identical:
        existing = matches.identical[0]
        if _is_deactivated(existing):
            message = _("%(model)s “%(name)s” exists, but is deactivated.")
        else:
            message = _("%(model)s “%(name)s” already exists.")
        form.add_error(field_name, message % {"model": model._meta.verbose_name, "name": existing})
    elif matches.similar and form.data.get("create_anyway") != _create_anyway_value(matches.similar):
        form.add_error(field_name, _("Similar entries exist, see below. Tick “Create anyway” if yours is another one."))


def similar_context(request, matches):
    """
    The context of ``theme/includes/_similar.html``, or None without matches.

    "Use this one" leads back to the form whose + opened the add page, with the
    entry preselected; on an add page opened otherwise it opens the entry's page.
    A deactivated entry has no link: neither the select nor its page shows it.
    """
    if not matches:
        return None
    blocked = bool(matches.identical)
    entries = matches.identical if blocked else matches.similar
    return {
        "blocked": blocked,
        "entries": [
            {
                "label": str(obj),
                "deactivated": _is_deactivated(obj),
                "use_url": None if _is_deactivated(obj) else _use_url(request, obj),
            }
            for obj in entries
        ],
        "create_anyway": None if blocked else _create_anyway_value(entries),
    }


def _name_words(values, similar_names):
    """The words of the compared fields in ``values``, a dict by field name."""
    text = " ".join(str(values.get(name) or "") for name in similar_names.fields)
    return words(text, similar_names.noise_words)


def _create_anyway_value(entries):
    """The "Create anyway" tick names the entries it was given for."""
    return ",".join(sorted(str(obj.pk) for obj in entries))


def _is_deactivated(obj):
    return getattr(obj, "deleted_at", None) is not None


def _use_url(request, obj):
    if request.GET.get("next_field"):
        url = get_redirect_url_after_add(request, obj.pk)
        if url:
            return url
    pages = get_related_pages(type(obj))
    if pages and request.user.has_perm(pages.permission("view")):
        return reverse(pages.detail_url, args=[obj.pk])
    return None
