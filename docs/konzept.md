<!--
SPDX-FileCopyrightText: 2026 Thomas Breitner

SPDX-License-Identifier: EUPL-1.2
-->

# Konzept

Die DLCDB verwaltet nicht einfach Geräte — sie verwaltet deren
Lebenszyklus. Jedes Gerät (*Device*) sammelt im Laufe seines Lebens eine
Kette von Zustandseinträgen (*Records*): bestellt, lokalisiert,
verliehen, nicht auffindbar, entfernt. Aus dieser einfachen Idee ergeben
sich die meisten Stärken der DLCDB von selbst: eine lückenlose Historie,
ein eingebauter Audit-Trail und ein Datenmodell, das man in fünf Minuten
verstanden hat.

## Device und Records: der Lebenszyklus als Kette

Ein *Device* ist der zentrale Stammdatensatz eines IT-Assets (EDV-Nummer,
Inventarnummer, Seriennummer, Typ, Hersteller, …). Der aktuelle Zustand
eines Devices wird aber nicht am Device selbst gespeichert, sondern als
*Record*:

- Ein Device hat zu jedem Zeitpunkt **genau einen aktiven Record**.
- Eine Zustandsänderung (Umzug, Verleih, Ausmusterung, …) **legt immer
  einen neuen Record an**. Der bisherige Record wird dabei nicht
  verändert oder gelöscht, sondern nur geschlossen (er erhält einen
  `effective_until`-Zeitstempel).
- Records sind damit **append-only**: Es kommt immer nur etwas dazu,
  nichts wird überschrieben.

Die möglichen Record-Typen und ihre erlaubten Übergänge:

```{eval-rst}
.. mermaid::

   stateDiagram-v2
      direction LR
      [*] --> LOKALISIERT
      LOKALISIERT --> LOKALISIERT : Umzug
      LOKALISIERT --> VERLIEHEN : Ausleihe
      LOKALISIERT --> NICHT_AUFFINDBAR
      LOKALISIERT --> ENTFERNT : Ausmusterung
      VERLIEHEN --> LOKALISIERT : Rückgabe
      VERLIEHEN --> NICHT_AUFFINDBAR
      NICHT_AUFFINDBAR --> LOKALISIERT : wiedergefunden
      NICHT_AUFFINDBAR --> ENTFERNT
      ENTFERNT --> [*]
```

Maßgeblich ist jeweils der **Schlüssel** (`INROOM`, `LENT`, …): er steht so in
der Datenbank, wird von der `CheckConstraint` geprüft und von der API
unverändert ausgeliefert. Die Beschriftungen daneben sind übersetzbar
(`gettext`) und können sich je nach Sprache ändern.

| Schlüssel | Beschriftung (de) | Bedeutung |
|---|---|---|
| `INROOM` | Lokalisiert | Das Device befindet sich in einem Raum. |
| `LENT` | Verliehen | Das Device ist an eine Person verliehen. |
| `LOST` | Nicht auffindbar | Das Device konnte (z.B. bei einer Inventur) nicht aufgefunden werden. |
| `REMOVED` | Entfernt | Das Device wurde ausgemustert (verkauft, verschrottet, …). Endzustand. |
| `ORDERED` | Bestellt | Sonderfall für bestellte, noch nicht in Betrieb genommene Geräte; wird nur über den Django-Admin gepflegt. |

Daneben existiert der Typ *Lizenz-Record* für Software-Lizenzen und
Verträge — siehe [Lizenzen](guides/lizenzen.md).

## Historie und Audit-Trail gratis

Weil Records nie verändert, sondern nur angehängt werden, ist die
komplette Gerätehistorie einfach *da* — ohne separates Logging, ohne
Zusatzmodul:

- Die Record-Kette eines Devices beantwortet Fragen wie „Wo war dieses
  Notebook im März?", „Wer hatte es ausgeliehen?" oder „Wann und mit
  welchem Verbleib wurde es ausgemustert?" — inklusive Zeitstempel und
  Bearbeiter.
- Die Detailseite eines Devices zeigt den aktiven Record; über *Verlauf
  › Alle Zustände* ist die vollständige, chronologische Kette erreichbar.
- Zusätzlich werden Änderungen an den Stammdaten eines Devices
  feldgenau versioniert (django-simple-history), einsehbar über die
  *History* im Django-Admin.

Für Nachweispflichten (z.B. gegenüber Verwaltung oder Revision) ist
damit kein zusätzlicher Prozess nötig: Der Audit-Trail ist das
Datenmodell.

## Einfacher Betrieb

Die DLCDB setzt konsequent auf einen "schmalen" Technik-Stack:

- **SQLite als Datenbank.** Die gesamte Datenbank ist eine einzelne
  Datei. Lesezugriffe sind sehr schnell, ein Datenbankserver muss weder
  installiert, noch abgesichert, noch aktualisiert werden. Backup heißt:
  das `data/`-Verzeichnis kopieren. Dank WAL-Modus blockieren sich
  Lese- und Schreibzugriffe im Alltagsbetrieb nicht.
- **Server-gerendertes UI.** Django-Templates mit Bootstrap 5 und htmx
  für partielle Updates — keine Single-Page-App, kein separates
  Frontend-Deployment, keine API-Synchronisationsprobleme.
- **Rechtegesteuerte Navigation.** Menüpunkte erscheinen nur, wenn die
  angemeldete Person die nötige Berechtigung hat. Die Oberfläche bleibt
  für jede Rolle übersichtlich.
- **Ein Prozess plus ein Worker.** Neben dem Webprozess läuft genau ein
  huey-Worker für Hintergrundaufgaben (Benachrichtigungen,
  HR-Sync) — ebenfalls SQLite-basiert, ohne Redis oder Message-Broker.

![Device-Detailseite mit aktivem Record und Historie](/_static/device-detail.webp){.sd-card}
