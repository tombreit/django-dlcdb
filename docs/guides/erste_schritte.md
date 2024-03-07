# Erste Schritte


## Benutzer und Gruppen einrichten

1. Gruppen anlegen
   Via: *Start › Authentifizierung und Autorisierung › Gruppen*. Es empfieht sich, für Alltagsaufgaben eine Gruppe mit eingeschränkten Rechten zu verwenden. 
1. Permissions für Gruppen vergeben
   Für jedes Model/View lassen sich einer Gruppe Berechtigungen/Permissions zuordnen. Es stehen für fast alle Models/Views die folgenden Berechtigungen zur Verfügung:
   * *Can add*
   * *Can change*
   * *Can delete*
   * *Can view*
1. User einrichten + Gruppen zuordnen
   Via: *Start › Accounts › Benutzer*. 


:::{admonition} **LDAP**
:class: note

Wenn für Ihre DLCDB die Anmeldung via LDAP konfiguriert ist, werden bestimmte LDAP-Gruppen in das DLCDB-Gruppenverzeichnis gespiegelt. Die Rechtezuweisung erfolgt dann über diese Gruppen. User/Benutzer werden bei erfolgreicher Anmeldung via LDAP automatisch in *Start › Accounts › Benutzer* angelegt.
:::


## Branding

Branding-Einstellungen wie z.B. Logo und Organisationsname sind via *Start › Organization › Branding* vorzunehmen. 

Werden keine Branding-Einstellungen vorgenommen, firmiert die die DLCDB als "DLCDB Corporation".


## Räume anlegen

Via *Start › DLCDB Core › Räume* oder über das Menü *Datenhaltung*.

Es muss mindestens ein Raum als *Extern/Verliehen-Raum* und ein Raum als *"Auto return" Raum* definiert sein. Wird ein Raum als solcher definiert, wird dieses Attribut bisher vorhandenen Raums bei diesem entfernt.

- *Extern/Verliehen-Raum*
  Devices, die z.B. beim Verleih keinem Raum zugeordnet werden können - z.B. ein Smartphone oder eine Homeoffice-Monitor - werden in manchen DLCDB-Prozessen (z.B. Inventur) diesem Raum zugeordnet.

- *"Auto return" Raum*
  Wird eine Ausleihe zurückgegeben, wird das Device automatisch diesem Raum zugeordnet. Dies kann z.B. ein Lagerraum oder der Helpdesk sein.

:::{admonition} **Gebäude/Locations**
:class: tip

Sollen Räume mehrer Standorte oder Gebäude verwaltet werden, oder werden kleinteiligere Einheiten als ein Raum benötigt, so kann dies über ein Bezeichnungsschema erfolgen. Beispiel: Eine Storage-Einheit im `Rack 32` in Raum `456` am Standort `Berlin Mitte` könnte folgende Raumnummer ergeben: `BM-456-R32`.
:::


## Personen anlegen

Via *Start › DLCDB Core › Personen* oder den Menüpunkt in "Datenhaltung".

:::{admonition} **Personen vs. User**
:class: tip

*Personen* sind "Kunden" der DLCDB, z.B. Personen, denen etwas ausgeliehen wird.

*User* oder *Benutzer* der DLCDB sind Menschen, die mit der DLCDB arbeiten und sich an der DLCDB anmelden müssen.
:::


## Devices anlegen

Via *Start › DLCDB Core › Devices* oder die entsprechenden Menüpunkte.

:::{tip}
Auf der Devices-Übersicht ist rechts oben ein Button *Device hinzufügen*.
:::


## Devices zuordnen

Die DLCDB verwaltet im Grunde nicht nur Devices, sondern vor allem die unterschiedlichen Stauts (in der DLCDB genannt *Records*), die ein Device in seinem Lebenscyclus durchgeht. 

Als Status oder *Record* stehen zur Verfügung:

1. Lokalisiert → Device ist einem Raum zugeordnet
1. Verleih → Device ist an eine Person verliehen
1. Nicht auffindbar → Verbleib des Devices ist aktuell nicht kla
1. Entfernt → Device ist z.B. ausgemustert und verschrottet

Jedes Device kann zu einem Zeitpunkt nur einem *Record* zugeordnet sein. 

Die DLCDB kann nur sinnvoll Devices verwalten, wenn die entsprechenden *Records* zugewiesen werden. Nach dem Anlegen eines Devices sollte demnach direkt ein *Record* zugeordnet werden.
