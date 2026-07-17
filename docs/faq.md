# FAQ

`````{dropdown} Warum kann ich keinen Hersteller oder Zulieferer bearbeiten oder zuordnen?

Ihr Benutzeraccount bzw. ihre Gruppenzugehörigkeiten bestimmen die Berechtigungen in der DLCDB. In den meisten Fällen fehlt eine entsprechende Berechtigung. Siehe [Berechtigungen](./guides/erste_schritte.md#benutzer-gruppen-und-tenants-einrichten)
`````

`````{dropdown} Warum sehe ich einen Menüpunkt nicht?

Menüpunkte im Frontend sind an Berechtigungen gebunden – ein Menüpunkt erscheint nur, wenn Ihre Gruppe die passende Berechtigung besitzt. Welche Berechtigung welchen Menüpunkt freischaltet (und warum manche Berechtigungen unter *Core* gelistet sind), zeigt [Navigation über Berechtigungen steuern](./guides/erste_schritte.md#navigation-über-berechtigungen-steuern). Hinweis: Superuser sehen alle Menüpunkte unabhängig von Berechtigungen.
`````

`````{dropdown} No tenant set?

Hinweis, dass dem aktuell angemeldeten Benutzer noch kein Tenant zugeordnet ist. Benutzer haben nur Zugriff auf Geräte, die dem selben Tenant zugeordnet sind. Superuser haben auf alle Geräte - unabhängig - von deren Tenant Zugriff.

Siehe [Tenant anlegen](./guides/erste_schritte.md#benutzer-gruppen-und-tenants-einrichten), [Tenant Model](./betrieb/model.md#tenant)
`````

`````{dropdown} Wo finde ich weitere Django-Admin Module?

Die Django-Admin Auflistung der verfügbaren Module ist unter https://fqdn/admin/ abrufbar.
`````

`````{dropdown} Wo ist die Historie eines Devices?

Die Detailseite eines Devices (*Hauptmenü › Geräte* › Gerät öffnen) zeigt den aktiven Record. Über *Verlauf › Alle Zustände* in der Seitenleiste ist die vollständige, chronologische Record-Kette des Devices erreichbar — wo war das Gerät wann, an wen war es verliehen, wann wurde es ausgemustert.

Zusätzlich werden Änderungen an den Stammdaten eines Devices feldgenau versioniert und sind über die *History* im Django-Admin einsehbar.

Siehe [Historie und Audit-Trail](./konzept.md#historie-und-audit-trail-gratis).
`````

`````{dropdown} Was ist ein "Record"?

Ein *Record* ist ein Statuszustand eines Devices, z.B. *Lokalisiert*, *Verliehen* oder *Entfernt*. Ein Device hat zu jedem Zeitpunkt genau einen aktiven Record; jede Statusänderung legt einen neuen Record an, ohne die bisherigen zu verändern. So entsteht automatisch die lückenlose Historie eines Devices.

Siehe [Konzept](./konzept.md).
`````

`````{dropdown} Was ist ein "Auto-Return-Raum"?

Siehe [Räume anlegen](./guides/erste_schritte.md#räume-anlegen)
`````

`````{dropdown} Was ist ein "Extern-Raum"?

Siehe [Räume anlegen](./guides/erste_schritte.md#räume-anlegen)
`````

`````{dropdown} Was ist "Kleinkram"?

Siehe [Kleinkram](guides/kleinkram.md) 
`````
