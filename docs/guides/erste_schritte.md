# Erste Schritte

Die DLCDB ist [installiert](../betrieb/setup.md) und ein Superuser ist mit `./manage.py createsuperuser` angelegt. Die folgenden Schritte richten eine frisch installierte DLCDB für den Alltag ein; bis Mandanten, Gruppen, Räume und die IT-Kontakt-Email da sind, erinnert ein Hinweis auf jeder Seite daran, mit einem Link dorthin. Wie Benutzer, Gruppen, Berechtigungen und Mandanten zusammenhängen, erklärt [Berechtigungen](berechtigungen.md).

## 1. Als Superuser anmelden

Der Superuser dient der Einrichtung. Für die tägliche Arbeit werden Benutzerkonten ohne Sonderrechte verwendet (siehe [Drei Stufen](berechtigungen.md#drei-stufen-benutzer-staff-superuser)).

## 2. Organisation

Logo und Organisationsname unter *Einstellungen › Organisation* eintragen.

## 3. Mandant anlegen

Via *Einstellungen › Mandanten › Mandant hinzufügen*. Ohne Gruppe, die ihn sieht, sieht niemand seine Geräte: das erledigt Schritt 4 (siehe [Mandanten](berechtigungen.md#mandanten)).

## 4. Gruppen anlegen

Via *Einstellungen › Gruppen und Berechtigungen › Neue Gruppe*: eine Gruppe je Rolle (z.B. Helpdesk, Inventur, Stammdaten), mit dem Mandanten aus Schritt 3, ihren Berechtigungen (ein Gruppenprofil kreuzt einen Anfang an) und ihren Mitgliedern. Sich selbst in eine Gruppe aufnehmen, die jeden Mandanten sieht: Auch ein Superuser sieht Geräte nur über seine Gruppen. Mit LDAP siehe [LDAP](berechtigungen.md#ldap).

## 5. Benutzer anlegen

Via *Einstellungen › Benutzer › Neuer Benutzer*: Konto anlegen und gleich den Gruppen aus Schritt 4 zuordnen. Mit LDAP entstehen die Konten beim ersten Login.

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

### Räume umbenennen

Ändert sich das Bezeichnungsschema, benennt *Räume umbenennen* (Button in der Raumübersicht) viele Räume auf einmal um. Ein regulärer Ausdruck (Python-Syntax) wird auf jede Raumnummer angewandt; umbenannt werden nur Räume, deren Nummer das Muster trifft. Beispiel: Muster `^(\d+)$` und Ersetzung `G\1` stellen allen reinen Ziffernnummern das Gebäude voran, aus `235` wird `G235`.

Die Vorschau zeigt, welcher Raum welche Nummer bekommt; umbenannt wird erst nach der Bestätigung. Ein Raum behält seine Nummer, wenn die neue leer, zu lang oder schon vergeben ist, auch in anderer Schreibweise oder an einen deaktivierten Raum. Tauschen oder verketten (`1` → `G1`, während `G1` → `GG1`) geht nicht in einem Schritt. Deaktivierte Räume werden nicht umbenannt. Nach der Bestätigung geht es zurück zur Raumübersicht; Räume, die ihre Nummer behalten haben, nennt dort eine Meldung mit dem Grund. Jede Umbenennung steht im Journal.

:::{note}
Ein späterer CSV-[Import](import.md) muss die neuen Nummern verwenden: Eine alte Nummer wie `235` legt sonst wieder einen eigenen Raum an.
:::

## 7. Personen anlegen

Via Menü *Datenhaltung › Personen*. *Personen* sind „Kunden“ der DLCDB (z.B. Entleihende), keine Benutzerkonten – siehe [Benutzer und Personen](berechtigungen.md#benutzer-und-personen). Bei angebundenem HR-System werden Personen automatisch abgeglichen (siehe [HR-Sync](../betrieb/hr-sync.md)). Organisationseinheiten und Positionen der Personen stehen unter *Einstellungen › Organisation*.

## 8. Devices anlegen

Via Menü *Geräte* (Hauptmenü), Button *Gerät hinzufügen* rechts oben. Viele Geräte auf einmal lassen sich per CSV [importieren](import.md).

![Geräte-Übersicht](/_static/devices-index.webp){.sd-card}

## 9. Devices einen Status geben

Ein Device braucht einen Status (*Record*), damit die DLCDB es verwalten kann – siehe [Konzept](../konzept.md). Nach dem Anlegen deshalb auf der Detailseite über *Neuer Zustand* *Lokalisieren* oder *Bestellung* wählen.
