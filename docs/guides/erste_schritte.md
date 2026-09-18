# Erste Schritte

Die DLCDB ist [installiert](../betrieb/setup.md) und ein Superuser ist mit `./manage.py createsuperuser` angelegt. Die folgenden Schritte richten eine frisch installierte DLCDB für den Alltag ein. Wie Benutzer, Gruppen, Berechtigungen und Tenants zusammenhängen, erklärt die Seite [Berechtigungen](berechtigungen.md).

## 1. Als Superuser anmelden

Der Superuser dient der Einrichtung und Administration. Für die tägliche Arbeit werden anschließend Gruppen mit eingeschränkten Rechten und normale Benutzerkonten verwendet.

## 2. Branding

Logo und Organisationsname werden unter *Start › Organization › Branding* eingetragen. Ohne diese Einstellungen firmiert die DLCDB als „DLCDB Corporation“.

## 3. Gruppen anlegen und Berechtigungen vergeben

Via *Start › Authentifizierung und Autorisierung › Gruppen*. Eine Gruppe je Rolle (z.B. Helpdesk, Inventur, Stammdaten) – Vorschläge stehen unter [Beispiel-Gruppen](berechtigungen.md#beispiel-gruppen).

Welche Berechtigung welchen Menüpunkt freischaltet, zeigt die Tabelle [Navigation](berechtigungen.md#navigation); welche Berechtigung welchen Statuswechsel erlaubt, die Tabelle [Statuswechsel](berechtigungen.md#statuswechsel).

:::{admonition} **LDAP**
:class: note

Ist die Anmeldung via LDAP konfiguriert, werden die in `AUTH_LDAP_MIRROR_GROUPS` genannten LDAP-Gruppen als DLCDB-Gruppen gespiegelt. Die Berechtigungen werden dann diesen gespiegelten Gruppen zugewiesen; Benutzer entstehen automatisch beim ersten Login.
:::

## 4. Tenant anlegen

Via *Start › Tenants › Tenant hinzufügen*: Name vergeben und die Gruppe(n) aus Schritt 3 zuordnen. Ein Benutzer sieht nur Geräte des Tenants, zu dem seine Gruppen gehören – ohne passende Gruppe sieht er keine Geräte (siehe [Tenants](berechtigungen.md#tenants)).

## 5. Benutzer anlegen

Via *Start › Accounts › Benutzer*: Konto anlegen und den Gruppen aus Schritt 3 zuordnen. Das Staff-Flag ist nur für Zugang zum Django-Admin nötig, das Superuser-Flag für die Administration (siehe [Drei Stufen](berechtigungen.md#drei-stufen-benutzer-staff-superuser)).

:::{tip}
Zum Prüfen der Rechtevergabe ein **Nicht-Superuser**-Konto verwenden – Superuser sehen alles, unabhängig von Berechtigungen.
:::

## 6. Räume anlegen

Via Menü *Datenhaltung › Räume*: Die Raumübersicht bietet rechts oben einen Button zum Anlegen neuer Räume.

Es muss mindestens ein Raum als *Extern/Verliehen-Raum* und ein Raum als *„Auto return“-Raum* markiert sein. Diese Markierung kann jeweils nur ein Raum tragen: Wird sie einem Raum gegeben, verliert sie der bisher markierte Raum.

* *Extern/Verliehen-Raum*
  Devices, die z.B. beim Verleih keinem Raum zugeordnet werden können – z.B. ein Smartphone oder ein Homeoffice-Monitor – werden in manchen DLCDB-Prozessen (z.B. Inventur) diesem Raum zugeordnet.

* *„Auto return“-Raum*
  Wird eine Ausleihe zurückgegeben, wird das Device automatisch diesem Raum zugeordnet. Dies kann z.B. ein Lagerraum oder der Helpdesk sein.

:::{admonition} **Gebäude/Locations**
:class: tip

Sollen Räume mehrerer Standorte oder Gebäude verwaltet werden, oder werden kleinteiligere Einheiten als ein Raum benötigt, so kann dies über ein Bezeichnungsschema erfolgen. Beispiel: Eine Storage-Einheit im `Rack 32` in Raum `456` am Standort `Berlin Mitte` könnte folgende Raumnummer ergeben: `BM-456-R32`.
:::

## 7. Personen anlegen

Via Menü *Datenhaltung › Personen*. *Personen* sind „Kunden“ der DLCDB (z.B. Entleihende), keine Benutzerkonten – siehe [Benutzer und Personen](berechtigungen.md#benutzer-und-personen). Bei angebundenem HR-System werden Personen automatisch abgeglichen (siehe [HR-Sync](../betrieb/hr-sync.md)).

## 8. Devices anlegen

Via Menü *Geräte* (Hauptmenü), Button *Gerät hinzufügen* rechts oben. Viele Geräte auf einmal lassen sich per CSV [importieren](import.md).

![Geräte-Übersicht](/_static/devices-index.webp){.sd-card}

## 9. Devices einen Status geben

Die DLCDB verwaltet im Grunde nicht nur Devices, sondern vor allem die unterschiedlichen Status (in der DLCDB genannt *Records*), die ein Device in seinem Lebenszyklus durchläuft — siehe [Konzept](../konzept.md).

Als Status oder *Record* stehen zur Verfügung:

1. Bestellt → Device ist bestellt, aber noch nicht eingetroffen
1. Lokalisiert → Device ist einem Raum zugeordnet
1. Verliehen → Device ist an eine Person verliehen
1. Nicht auffindbar → Verbleib des Devices ist aktuell nicht klar
1. Entfernt → Device ist z.B. ausgemustert und verschrottet

Jedes Device hat zu einem Zeitpunkt genau einen aktiven *Record*. Die DLCDB kann Devices nur sinnvoll verwalten, wenn sie einen Status haben: Nach dem Anlegen eines Devices sollte demnach direkt über *Neuer Zustand* auf der Detailseite ein Record vergeben werden (*Lokalisieren* oder *Bestellung*).
