# Erste Schritte

Die DLCDB ist [installiert](../betrieb/setup.md) und ein Superuser ist mit `./manage.py createsuperuser` angelegt. Die folgenden Schritte richten eine frisch installierte DLCDB für den Alltag ein. Wie Benutzer, Gruppen, Berechtigungen und Mandanten zusammenhängen, erklärt [Berechtigungen](berechtigungen.md).

## 1. Als Superuser anmelden

Der Superuser dient der Einrichtung. Für die tägliche Arbeit werden Benutzerkonten ohne Sonderrechte verwendet (siehe [Drei Stufen](berechtigungen.md#drei-stufen-benutzer-staff-superuser)).

## 2. Branding

Logo und Organisationsname unter *Einstellungen › Branding* eintragen.

## 3. Gruppen anlegen und Berechtigungen vergeben

Via *Start › Konten › Gruppen*: eine Gruppe je Rolle (z.B. Helpdesk, Inventur, Stammdaten), Vorschläge unter [Beispiel-Gruppen](berechtigungen.md#beispiel-gruppen). Welche Berechtigung was freischaltet, zeigen die Tabellen [Navigation](berechtigungen.md#navigation) und [Statuswechsel](berechtigungen.md#statuswechsel). Mit LDAP werden die Gruppen gespiegelt, siehe [LDAP](berechtigungen.md#ldap).

## 4. Mandant anlegen

Via *Einstellungen › Mandanten › Mandant hinzufügen*: Name vergeben und speichern, dann in der Mandanten-Übersicht in der Spalte des neuen Mandanten die Gruppe(n) aus Schritt 3 anhaken. Die Gruppe der Administratoren jedem Mandanten zuordnen, auch jedem später angelegten – ohne passende Gruppe sieht niemand Geräte (siehe [Mandanten](berechtigungen.md#mandanten)).

## 5. Benutzer anlegen

Via *Start › Konten › Benutzer*: Konto anlegen und den Gruppen aus Schritt 3 zuordnen. Mit LDAP entstehen die Konten beim ersten Login.

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

Ein Device braucht einen Status (*Record*), damit die DLCDB es verwalten kann – siehe [Konzept](../konzept.md). Nach dem Anlegen deshalb auf der Detailseite über *Neuer Zustand* *Lokalisieren* oder *Bestellung* wählen.
