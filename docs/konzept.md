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
  verändert oder gelöscht, sondern nur geschlossen.
- Records sind damit **append-only**: Es kommt immer nur etwas dazu,
  nichts wird überschrieben.

Welche Übergänge zwischen den Zuständen erlaubt sind, zeigt das Diagramm:

<!-- Das Diagramm gibt TRANSITIONS in dlcdb/core/lifecycle.py wieder;
     wird die Übergangstabelle geändert, hier mitpflegen. -->

```{eval-rst}
.. mermaid::

   stateDiagram-v2
      direction TB

      state "Bestellt · ORDERED" as ORDERED
      state "Lokalisiert · INROOM" as INROOM
      state "Verliehen · LENT" as LENT
      state "Nicht auffindbar · LOST" as LOST
      state "Entfernt · REMOVED" as REMOVED

      [*] --> ORDERED : Bestellung
      [*] --> INROOM : Lokalisieren
      ORDERED --> INROOM : Lokalisieren
      INROOM --> LENT : Ausleihe
      LENT --> INROOM : Rückgabe
      INROOM --> LOST : nicht auffindbar
      LENT --> LOST : nicht auffindbar
      LOST --> INROOM : gefunden
      INROOM --> REMOVED : Ausmusterung
      LENT --> REMOVED : Ausmusterung
      LOST --> REMOVED : Ausmusterung
      REMOVED --> INROOM : recover
      REMOVED --> LOST : restore

      note left of INROOM
        Umzug: neuer Record,
        Zustand bleibt INROOM
      end note

      classDef start fill:#eaf2fb,stroke:#3a6ea5,color:#1a1a1a
      classDef terminal fill:#ededed,stroke:#8a8a8a,color:#1a1a1a
      class ORDERED start
      class REMOVED terminal
```

Welche dieser Übergänge ein Benutzer angeboten bekommt, bestimmen seine
Berechtigungen, siehe [Statuswechsel](guides/berechtigungen.md#statuswechsel).

Die **Schlüssel** (`INROOM`, `LENT`, …) stehen so in der Datenbank, in der API
und im CSV-Import; die Beschriftungen sind übersetzt.

| Schlüssel | Beschriftung (de) | Bedeutung |
|---|---|---|
| `INROOM` | Lokalisiert | Das Device befindet sich in einem Raum. |
| `LENT` | Verliehen | Das Device ist an eine Person verliehen. |
| `LOST` | Nicht auffindbar | Das Device konnte (z.B. bei einer Inventur) nicht aufgefunden werden. |
| `REMOVED` | Entfernt | Das Device wurde ausgemustert (verkauft, verschrottet, …). Endzustand. |
| `ORDERED` | Bestellt | Bestelltes, noch nicht eingetroffenes Gerät. Optionaler Startzustand vor `INROOM`. |

Software-Lizenzen und Verträge sind Devices mit dem Schalter *Ist Lizenz?*
und durchlaufen dieselben Zustände — siehe [Lizenzen](guides/lizenzen.md).

## Historie und Audit-Trail

Weil Records nur angehängt werden, ist die Gerätehistorie ohne separates
Logging vollständig:

- Die Record-Kette beantwortet Fragen wie „Wo war dieses Notebook im
  März?", „Wer hatte es ausgeliehen?" oder „Wann und mit welchem Verbleib
  wurde es ausgemustert?" — mit Zeitstempel und Bearbeiter. Auf der
  Detailseite eines Devices: *Verlauf › Alle Zustände*.
- Änderungen an den Stammdaten eines Devices werden feldgenau
  versioniert: *Verlauf › Felder Historie* (wann, wer, welches Feld).

Für Nachweispflichten (z.B. gegenüber Verwaltung oder Revision) ist
damit kein zusätzlicher Prozess nötig.

## Einfacher Betrieb

Die DLCDB setzt konsequent auf einen "schmalen" Technik-Stack:

- **SQLite als Datenbank.** Die gesamte Datenbank ist eine einzelne
  Datei. Lesezugriffe sind sehr schnell, ein Datenbankserver muss weder
  installiert, noch abgesichert, noch aktualisiert werden; gesichert wird
  ein nächtlicher Snapshot (siehe [Backup](betrieb/setup.md#backup)). Dank
  WAL-Modus blockieren sich Lese- und Schreibzugriffe im Alltagsbetrieb nicht.
- **Server-gerendertes UI.** Django-Templates mit Bootstrap 5 und htmx
  für partielle Updates — keine Single-Page-App, kein separates
  Frontend-Deployment, keine API-Synchronisationsprobleme.
- **Ein Prozess plus ein Worker.** Neben dem Webprozess läuft genau ein
  huey-Worker für Hintergrundaufgaben (Benachrichtigungen,
  HR-Sync) — ebenfalls SQLite-basiert, ohne Redis oder Message-Broker.

![Device-Detailseite mit aktivem Record und Historie](/_static/device-detail.webp){.sd-card}
