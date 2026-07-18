# Geräte

Das *Device* (Gerät) ist der zentrale Stammdatensatz eines IT-Assets in der
DLCDB. Zustand, Standort und Historie werden nicht am Gerät selbst gespeichert,
sondern ergeben sich aus seiner Kette von *Records* — siehe
[Konzept](../konzept.md). Dieser Guide zeigt die beiden zentralen
Arbeitsflächen: die **Geräte-Übersicht** und die **Geräte-Detailseite**.

- Geräteverwaltung: {{ devices_fe_link }} (Hauptmenü *Geräte*)

## Geräte-Übersicht

![Geräte-Übersicht](/_static/devices-index.webp){.sd-card}

Die Übersicht listet alle Geräte und ist durchsuch-, filter- und sortierbar:

- **Suche** über IT-ID, Seriennummer, Modell, Inventarnummer, Hersteller u.a.
- **Filter**: *Typ* (Geräteklasse), *Status* (Zustand/Record), *Verleihbar*,
  *Raum*, *Hersteller* — sowie unter *Weitere Filter*: Lieferant, Importstatus
  und Dubletten (doppelte Seriennummer/Nickname).
- **Sortierung** über die anklickbaren Spaltenköpfe (Standard: zuletzt
  geändert zuerst).
- **Zählung** „X von Y Geräten" und **Pagination** (25 Geräte pro Seite);
  Filtern, Sortieren und Blättern aktualisieren die Liste ohne Neuladen.
- Button *Gerät hinzufügen* (rechts oben) legt ein neues Gerät an.

:::{note}
Nicht-Superuser sehen nur Geräte ihres Mandanten (*Tenant*). Superuser sehen
alle Geräte und zusätzlich die Spalte *Mandant*.
:::

## Geräte-Detailseite

![Geräte-Detailseite](/_static/device-detail.webp){.sd-card}

Ein Klick auf ein Gerät öffnet die Detailseite. Sie dient zugleich dem Ansehen
**und** Bearbeiten (nur mit Berechtigung *Can change device*, sonst
schreibgeschützt). Links das Formular, rechts eine Info-Spalte.

Das Formular ist in Sektionen gegliedert:

- **Identifizierung** — IT-ID, Inventarnummer (SAP-Nummer im Format
  `Hauptnummer-Unternummer`), Geräteklasse, Mandant sowie die Schalter
  *Ist verleihbar?* und *Ist Lizenz?*
- **Hersteller und Modell** — Hersteller, Modellbezeichnung, Seriennummer, Notiz
- **Beschaffung** — Bestell-/Vertragsdaten, Kostenstelle, Buchwert etc.
- **Namen und Netzwerk** — Nickname/C-Name, MAC-Adressen
- **Vertrauliche Daten** — z.B. Passwörter für Festplatten-/Backup-Verschlüsselung
  (nur eintragen, wenn betrieblich erforderlich)

Die Info-Spalte rechts zeigt:

- **Aktueller Status** — der aktive Record (Zustand, Raum/Person) und der Button
  *Neuer Zustand*. Dieser bietet nur die laut [Konzept](../konzept.md) erlaubten
  Übergänge — u.a. *Verschieben* → [Umziehen](umziehen.md) und *Verleihen* →
  [Ausleihe](ausleihe.md).
- **Verlauf** — *Alle Zustände* (vollständige Record-Kette) und *History*
  (feldgenaue Änderungshistorie).
- **Geräte-Details** — Admin-Ansicht, Erstellt/Zuletzt geändert, Ursprung, UUID.
- **QR-Code** — der automatisch erzeugte QR-Code des Geräts (für die
  [Inventur](inventur.md)).

:::{tip}
Nur Geräte mit gesetztem Schalter *Ist verleihbar?* erscheinen in der
[Verleihansicht](ausleihe.md).
:::

:::{note}
Ist *Ist Lizenz?* gesetzt, wird das Gerät als Software-Lizenz behandelt und über
die [Lizenzen](lizenzen.md)-Verwaltung geführt.
:::

## Verwandte Themen

- [Konzept](../konzept.md) — Devices, Records und Audit-Trail
- [Erste Schritte](erste_schritte.md) — Geräte anlegen und Records zuordnen
- [Import](import.md) — Geräte per CSV importieren
- [Umziehen](umziehen.md) · [Ausleihe](ausleihe.md) · [Inventur](inventur.md) · [Lizenzen](lizenzen.md)
