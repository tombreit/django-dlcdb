# FAQ

`````{dropdown} Warum kann ich keinen Hersteller oder Zulieferer bearbeiten oder zuordnen?

Ihr Benutzeraccount bzw. ihre Gruppenzugehörigkeiten bestimmen die Berechtigungen in der DLCDB. In den meisten Fällen fehlt eine entsprechende Berechtigung (hier: *Can change manufacturer* bzw. *Can change supplier*). Siehe [Gruppen und Berechtigungen](./guides/berechtigungen.md#gruppen-und-berechtigungen)
`````

`````{dropdown} Warum sehe ich einen Menüpunkt nicht?

Menüpunkte im Frontend sind an Berechtigungen gebunden – ein Menüpunkt erscheint nur, wenn Ihre Gruppe die passende Berechtigung besitzt. Welche Berechtigung welchen Menüpunkt freischaltet (und warum manche Berechtigungen unter *Core* gelistet sind), zeigt [Navigation](./guides/berechtigungen.md#navigation). Hinweis: Superuser sehen alle Menüpunkte unabhängig von Berechtigungen.
`````

`````{dropdown} None of your groups belongs to a tenant?

Keine Gruppe des Benutzers ist einem Tenant zugeordnet, deshalb sieht er keine Geräte – auch als Superuser. Abhilfe: eine seiner Gruppen dem Tenant zuordnen (*Start › Tenants › Tenant › Gruppen*).

Siehe [Tenants](./guides/berechtigungen.md#tenants), [Tenant anlegen](./guides/erste_schritte.md#4-tenant-anlegen), [Tenant Model](./betrieb/model.md#tenant)
`````

`````{dropdown} Wo finde ich weitere Django-Admin Module?

Die Django-Admin Auflistung der verfügbaren Module ist unter {{ base_url }}/admin/ abrufbar (Eintrag *Django Site-Verwaltung* im Benutzermenü; erfordert das Staff-Flag, siehe [Rolle des Django-Admins](./guides/berechtigungen.md#rolle-des-django-admins)).
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

Siehe [Räume anlegen](./guides/erste_schritte.md#6-räume-anlegen)
`````

`````{dropdown} Was ist ein "Extern-Raum"?

Siehe [Räume anlegen](./guides/erste_schritte.md#6-räume-anlegen)
`````

`````{dropdown} Was ist "Kleinkram"?

Siehe [Kleinkram](guides/kleinkram.md) 
`````
