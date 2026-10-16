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

Neben den Auswahlfeldern *Geräteklasse*, *Hersteller* und *Distributor* stehen
zwei Buttons: der Stift öffnet den gewählten Eintrag (ohne Änderungsrecht das
Auge, nur zum Ansehen), das Plus legt einen neuen an. Speichern oder Abbrechen
führt zurück zum Gerät; ein neu angelegter Eintrag ist dort schon ausgewählt
und wird mit dem Gerät gespeichert. Ungespeicherte Eingaben im Geräteformular
gehen auf dem Weg verloren, die DLCDB fragt vorher nach. Die Buttons erscheinen
nur mit den Berechtigungen der jeweiligen Seite, z.B. *Can view manufacturer*
und *Can add manufacturer*. Das Auswahlfeld *Raum* beim Wiedereingliedern eines
ausgemusterten Geräts hat dieselben Buttons.

Beim Anlegen vergleicht die DLCDB den Namen mit den vorhandenen Einträgen, auch
den deaktivierten, und zeigt die gefundenen schon während des Tippens an. Groß-
und Kleinschreibung, Umlaute, Satzzeichen und Zusätze wie *GmbH* zählen dabei
nicht: *pro-com* wird neben *Procom* nicht angelegt. Ein ähnlicher Name (*Pulse*
neben *Pulse Secure*, ein Tippfehler) wird erst nach Bestätigung angelegt. Ein
Button neben jedem gefundenen Eintrag übernimmt ihn stattdessen ins
Geräteformular. Dasselbe gilt für Räume (nur gleiche Nummern) und Personen.

Die Info-Spalte rechts zeigt:

- **Aktueller Status** — der aktive Record (Zustand, Raum/Person) und der Button
  *Neuer Zustand* mit den erlaubten Übergängen (siehe
  [Statuswechsel](berechtigungen.md#statuswechsel)), u.a. *Umziehen* →
  [Umziehen](umziehen.md), *Ausleihen* → [Ausleihe](ausleihe.md) und
  *Entfernen* → [Ausmustern](ausmustern.md).
- **Verlauf** — *Alle Zustände* (vollständige Record-Kette) und *Felder Historie*
  (feldgenaue Änderungen als Zeitleiste: wann, wer, was; die
  Verschlüsselungs-Passwörter nur maskiert).
- **Geräte-Details** — Erstellt/Zuletzt geändert, Ursprung, UUID.
- **QR-Code** — der automatisch erzeugte QR-Code des Geräts (für die
  [Inventur](inventur.md)).

:::{note}
Ist *Ist Lizenz?* gesetzt, wird das Gerät als Software-Lizenz behandelt und über
die [Lizenzen](lizenzen.md)-Verwaltung geführt. *Ist verleihbar?* entscheidet,
ob es in der [Verleihansicht](ausleihe.md) erscheint.
:::
