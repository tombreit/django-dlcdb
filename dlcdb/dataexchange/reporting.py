# SPDX-FileCopyrightText: Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

"""
Unified per-row result reporting for the import and decommissioning workflows.

A single ``OperationReport`` collects one ``RowResult`` per CSV row. It renders a
short, severity-aware summary for Django toast messages (``short_html``) and a
detailed plaintext log for the stored ``messages`` field (``detailed``).
"""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.html import format_html


class Outcome(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    SKIPPED = "SKIPPED"
    REMOVED = "REMOVED"
    ERROR = "ERROR"


@dataclass
class RowResult:
    row: int
    identifier: str
    outcome: Outcome
    detail: str = ""


@dataclass
class OperationReport:
    operation: str
    context: str = ""
    dry_run: bool = False
    rows: list[RowResult] = field(default_factory=list)

    def add(self, *, row, identifier, outcome, detail=""):
        self.rows.append(RowResult(row=row, identifier=identifier, outcome=outcome, detail=detail))

    @property
    def counts(self):
        result = {outcome: 0 for outcome in Outcome}
        for row in self.rows:
            result[row.outcome] += 1
        return result

    @property
    def level(self):
        counts = self.counts
        if counts[Outcome.ERROR]:
            return "error"
        if counts[Outcome.SKIPPED]:
            return "warning"
        return "success"

    def counts_summary(self):
        # Canonical order, non-zero outcomes only.
        parts = [f"{count} {outcome.value.lower()}" for outcome, count in self.counts.items() if count]
        return ", ".join(parts) if parts else "no rows"

    def short_html(self):
        prefix = "Dry run — " if self.dry_run else ""
        return format_html(
            "{}{}: {}.<br>See the saved log for per-row details.",
            prefix,
            self.operation,
            self.counts_summary(),
        )

    def detailed(self, *, verbose=True):
        """Plaintext log for the stored ``messages`` field.

        The counts line always reflects every row (so totals stay honest). When
        ``verbose`` is False, UNCHANGED rows are left out of the per-row listing
        to keep routine runs readable — the changed/created/error rows still show.
        """
        header = f"{self.operation}{' (dry run)' if self.dry_run else ''} {datetime.now():%Y-%m-%d %H:%M}"
        if self.context:
            header = f"{header} — {self.context}"
        counts_line = "  ".join(f"{outcome.value.title()}: {count}" for outcome, count in self.counts.items() if count)

        lines = [header, counts_line or "no rows", ""]
        for row in self.rows:
            if not verbose and row.outcome is Outcome.UNCHANGED:
                continue
            detail = f" ({row.detail})" if row.detail else ""
            lines.append(f"[row {row.row}] {row.identifier}  {row.outcome.value}{detail}")
        return "\n".join(lines)

    def persist(self, log_entry):
        """Store this report on a log model instance and save it.

        ``log_entry`` is any model with a ``messages`` field (and optionally
        ``status``/``summary``), e.g. an ``OperationLogBase`` subclass. Returns the
        saved instance. Per-row detail is verbose only when ``settings.DEBUG``.
        """
        log_entry.messages = self.detailed(verbose=settings.DEBUG)
        if hasattr(log_entry, "status"):
            log_entry.status = self.level
        if hasattr(log_entry, "summary"):
            log_entry.summary = self.counts_summary()
        log_entry.save()
        return log_entry
