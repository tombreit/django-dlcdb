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

Die Liste zeigt nur die Geräte der eigenen [Mandanten](berechtigungen.md#mandanten).

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
  *Neuer Zustand* mit den erlaubten Übergängen (siehe
  [Statuswechsel](berechtigungen.md#statuswechsel)), u.a. *Umziehen* →
  [Umziehen](umziehen.md) und *Ausleihen* → [Ausleihe](ausleihe.md).
- **Verlauf** — *Alle Zustände* (vollständige Record-Kette) und *Felder Historie*
  (feldgenaue Änderungen als Zeitleiste: wann, wer, was; die
  Verschlüsselungs-Passwörter nur maskiert).
- **Geräte-Details** — Admin-Ansicht, Erstellt/Zuletzt geändert, Ursprung, UUID.
- **QR-Code** — der automatisch erzeugte QR-Code des Geräts (für die
  [Inventur](inventur.md)).

:::{note}
Ist *Ist Lizenz?* gesetzt, wird das Gerät als Software-Lizenz behandelt und über
die [Lizenzen](lizenzen.md)-Verwaltung geführt. *Ist verleihbar?* entscheidet,
ob es in der [Verleihansicht](ausleihe.md) erscheint.
:::
