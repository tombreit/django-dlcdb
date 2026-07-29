# Erste Schritte

## Benutzer, Gruppen und Tenants einrichten

1. Gruppen anlegen

   Via: *Start › Authentifizierung und Autorisierung › Gruppen*. Es empfiehlt sich, für Alltagsaufgaben eine Gruppe mit eingeschränkten Rechten zu verwenden.

1. Permissions für Gruppen vergeben

   Für jedes Model/View lassen sich einer Gruppe Berechtigungen/Permissions zuordnen. Es stehen für fast alle Models/Views die folgenden Berechtigungen zur Verfügung:

   * *Can add*
   * *Can change*
   * *Can delete*
   * *Can view*

   Zudem existieren spezielle Berechtigungen, z.B. zum Durchführen von Inventuren (*Can inventorize*) sowie für die einzelnen Statuswechsel eines Geräts (siehe [Statuswechsel über Berechtigungen steuern](#statuswechsel-uber-berechtigungen-steuern)).

1. User einrichten + Gruppen zuordnen

   Via: *Start › Accounts › Benutzer*.

1. Tenant einrichten

   Via: *Home/Start > Tenants > Add Tenant* einen Tenant anlegen und dem Tenant eine Gruppe zuordnen.

:::{admonition} **LDAP**
:class: note

Wenn für Ihre DLCDB die Anmeldung via LDAP konfiguriert ist, werden bestimmte LDAP-Gruppen in das DLCDB-Gruppenverzeichnis gespiegelt. Die Rechtezuweisung erfolgt dann über diese Gruppen. User/Benutzer werden bei erfolgreicher Anmeldung via LDAP automatisch in *Start › Accounts › Benutzer* angelegt.
:::

## Navigation über Berechtigungen steuern

Die Menüpunkte im Frontend sind an Berechtigungen gebunden: Ein Menüpunkt erscheint für einen Benutzer nur dann, wenn dessen Gruppe die passende *view*-Berechtigung (bzw. die in der Tabelle genannte Berechtigung) des zugrundeliegenden Models besitzt. Wer einem Benutzer einen bestimmten Menüpunkt geben möchte, weist der Gruppe des Benutzers die entsprechende Berechtigung zu (*Start › Authentifizierung und Autorisierung › Gruppen*).

:::{warning}
**Superuser sehen alle Menüpunkte** – unabhängig von den zugewiesenen Berechtigungen. Um zu prüfen, ob ein Menüpunkt tatsächlich durch eine Berechtigung sichtbar wird, verwenden Sie einen **Nicht-Superuser** (sonst erscheint der Menüpunkt auch ohne die Berechtigung).
:::

:::{admonition} **Berechtigung unter *Core* finden**
:class: note

Einige Menüpunkte gehören technisch zur App *Core*, obwohl sie in einem anderen Menübereich erscheinen (Proxy-Modelle). Die passende Berechtigung ist dann in der Gruppen-Auswahl unter **Core** gelistet – nicht unter dem gleichnamigen Menü. Beispiel: Der Menüpunkt *Ausleihe* benötigt die Berechtigung **Core | lent record | Can view lent record** (`core.view_lentrecord`), nicht eine Berechtigung unter „Lending“.
:::

<!-- Diese Tabelle spiegelt die "required_permission"-Werte aus den
     dlcdb/*/navigation.py-Dateien wider. Bei Änderungen an den Menüs
     (Hinzufügen/Entfernen von Navigationseinträgen) hier nachziehen. -->

| Menüpunkt (Bereich) | Berechtigung (Django-Admin-Anzeige) | codename |
|---|---|---|
| Ausleihe (Hauptmenü) | Core \| lent record \| Can view lent record | `core.view_lentrecord` |
| Geräte (Hauptmenü) | Core \| device \| Can view device | `core.view_device` |
| Umziehen (Hauptmenü) | Core \| record \| eine der drei Bewegungs-Berechtigungen | `core.transition_can_locate_device`, `core.transition_can_relocate_device` oder `core.transition_can_find_device` |
| Inventarisieren (Hauptmenü) | Core \| … \| Can inventorize | `core.can_inventorize` |
| Kleinkram (Hauptmenü) | Smallstuff \| assigned thing \| Can view assigned thing | `smallstuff.view_assignedthing` |
| Lizenzen (Hauptmenü) | *nur Anmeldung erforderlich* | — |
| Datenhaltung › Räume | Core \| room \| Can view room | `core.view_room` |
| Datenhaltung › Hersteller | Core \| manufacturer \| Can view manufacturer | `core.view_manufacturer` |
| Datenhaltung › Zulieferer | Core \| supplier \| Can view supplier | `core.view_supplier` |
| Datenhaltung › Geräteklassen | Core \| device type \| Can view device type | `core.view_devicetype` |
| Datenhaltung › Personen | Core \| person \| Can view person | `core.view_person` |
| Datenhaltung › Records / Entfernt-Records | Core \| record \| Can view record | `core.view_record` |
| Datenhaltung › Inventuren | Core \| inventory \| Can change inventory | `core.change_inventory` |
| Datenhaltung › Notizen | Core \| note \| Can view note | `core.view_note` |
| Prozesse › Bulk Import | Data Exchange \| importer list \| Can view importer list | `dataexchange.view_importerlist` |
| Prozesse › Bulk Ausmusterung | Data Exchange \| remover list \| Can view remover list | `dataexchange.view_removerlist` |
| Prozesse › SAP-Abgleich | Core \| inventory \| Can change inventory | `core.change_inventory` |
| Einstellungen › Ausleihe Konfiguration | Lending \| lending configuration \| Can view lending configuration | `lending.view_lendingconfiguration` |
| Einstellungen › Ausleih-Profile | Lending \| lending profile \| Can view lending profile | `lending.view_lendingprofile` |
| Einstellungen › Lizenzmodul Konfiguration | Licenses \| licenses configuration \| Can view licenses configuration | `licenses.view_licensesconfiguration` |
| Einstellungen › Branding | Organization \| branding \| Can view branding | `organization.view_branding` |
| Einstellungen › HR-API-Sync-Konfiguration | Data Exchange \| HR API Sync Configuration \| Can view HR API Sync Configuration | `dataexchange.view_udbsyncconfiguration` |

:::{tip}
Ist die Anmeldung via LDAP konfiguriert, weisen Sie diese Berechtigungen den **gespiegelten Gruppen** zu (siehe LDAP-Hinweis oben unter „Benutzer, Gruppen und Tenants einrichten“). Manuell in der DLCDB angelegte Gruppenzugehörigkeiten können bei der nächsten Anmeldung durch die LDAP-Spiegelung überschrieben werden.
:::

## Statuswechsel über Berechtigungen steuern

Welche Statuswechsel (*Records*) einem Benutzer für ein Gerät angeboten werden, ist an Berechtigungen gebunden. Jeder Übergang im Gerätelebenszyklus hat eine eigene Berechtigung; angeboten wird ein Übergang genau dann, wenn er vom aktuellen Status aus überhaupt zulässig ist **und** der Benutzer die zugehörige Berechtigung besitzt.

Damit entscheidet die Rechtevergabe – nicht der Programmcode –, welche Aktionen eine Gruppe im Alltag sieht. Alle Berechtigungen sind in der Gruppen-Auswahl unter **Core | record** gelistet.

| Aktion | Übergang | Berechtigung (Django-Admin-Anzeige) | codename |
|---|---|---|---|
| Bestellt | *(kein Record)* → Bestellt | Core \| record \| Transition: Can record a device as ordered | `core.transition_can_order_device` |
| Lokalisieren | *(kein Record)*/Bestellt → Im Raum | Core \| record \| Transition: Can localise a device for the first time | `core.transition_can_locate_device` |
| Umziehen | Im Raum → Im Raum | Core \| record \| Transition: Can move a device to another room | `core.transition_can_relocate_device` |
| Verleihen und Zurücknehmen | Im Raum ↔ Verliehen | Core \| record \| Transition: Can lend a device and take it back | `core.transition_can_lend_device` |
| Nicht auffindbar | Im Raum/Verliehen/Nicht auffindbar → Nicht auffindbar | Core \| record \| Transition: Can mark a device as not locatable | `core.transition_can_lose_device` |
| Wiedergefunden | Nicht auffindbar → Im Raum | Core \| record \| Transition: Can mark a lost device as found | `core.transition_can_find_device` |
| Ausmustern | fast jeder Status → Entfernt | Core \| record \| Transition: Can remove (decommission) a device | `core.transition_can_remove_device` |
| Ausmusterung rückgängig | Entfernt → Nicht auffindbar | Core \| record \| Transition: Can restore a removed device to not-locatable | `core.transition_can_restore_device` |
| Wiedereingliedern | Entfernt → Im Raum | Core \| record \| Transition: Can recover a removed device into a room | `core.transition_can_recover_device` |

:::{warning}
**Superuser sehen alle zulässigen Statuswechsel** – auch die beiden Wege aus dem Status *Entfernt* heraus. Zum Prüfen einer Rechtevergabe daher immer einen **Nicht-Superuser** verwenden.
:::

:::{admonition} **Ausmusterung rückgängig machen**
:class: note

`transition_can_restore_device` und `transition_can_recover_device` sind nach der Installation **keiner Gruppe zugewiesen**. Ein ausgemustertes Gerät ist damit standardmäßig ein Endpunkt. Wer diese Wege öffnen möchte, weist die Berechtigungen bewusst zu – üblicherweise nur einer eng gefassten Gruppe.

Beide Übergänge waren technisch immer zulässig (Inventur, Superuser-Aktion im Admin), wurden bisher aber nirgends angeboten.
:::

:::{admonition} **Umstellung bestehender Installationen**
:class: note

Früher wurden Statuswechsel über die *Can add*-Berechtigung des jeweils geschriebenen Records gesteuert (z.B. `core.add_inroomrecord`), die Ausleihe zusätzlich über `core.change_lentrecord`. Bei der Migration erhalten alle Gruppen und Benutzer automatisch die neuen Berechtigungen, die ihren bisherigen Rechten entsprechen – niemand verliert oder gewinnt dabei eine Fähigkeit. Die alten `add_*`- und `change_*`-Berechtigungen bleiben bestehen, steuern die Statuswechsel aber nicht mehr.
:::

:::{admonition} **Die Berechtigung gilt für die ganze Aktion**
:class: tip

Eine Berechtigung schaltet nicht nur den Button auf der Geräteseite frei, sondern auch die dahinterliegende Ansicht und deren Geräteauswahl. Wer z.B. nur `core.transition_can_find_device` besitzt, findet im Menüpunkt *Umziehen* ausschließlich die als *nicht auffindbar* markierten Geräte – und kann genau diese wieder einem Raum zuordnen. Ein Button, der anschließend in einer Fehlermeldung endet, kann so nicht mehr entstehen.
:::

## Branding

Branding-Einstellungen wie z.B. Logo und Organisationsname sind via *Start › Organization › Branding* vorzunehmen.

Werden keine Branding-Einstellungen vorgenommen, firmiert die DLCDB als "DLCDB Corporation".

## Räume anlegen

Via Menü *Datenhaltung › Räume*: Die Raumübersicht bietet rechts oben
einen Button zum Anlegen neuer Räume.

Es muss mindestens ein Raum als *Extern/Verliehen-Raum* und ein Raum als *"Auto return" Raum* definiert sein. Wird ein Raum als solcher definiert, wird dieses Attribut bisher vorhandenen Raums bei diesem entfernt.

* *Extern/Verliehen-Raum*
  Devices, die z.B. beim Verleih keinem Raum zugeordnet werden können - z.B. ein Smartphone oder eine Homeoffice-Monitor - werden in manchen DLCDB-Prozessen (z.B. Inventur) diesem Raum zugeordnet.

* *"Auto return" Raum*
  Wird eine Ausleihe zurückgegeben, wird das Device automatisch diesem Raum zugeordnet. Dies kann z.B. ein Lagerraum oder der Helpdesk sein.

:::{admonition} **Gebäude/Locations**
:class: tip

Sollen Räume mehrerer Standorte oder Gebäude verwaltet werden, oder werden kleinteiligere Einheiten als ein Raum benötigt, so kann dies über ein Bezeichnungsschema erfolgen. Beispiel: Eine Storage-Einheit im `Rack 32` in Raum `456` am Standort `Berlin Mitte` könnte folgende Raumnummer ergeben: `BM-456-R32`.
:::

## Personen anlegen

Via Menü *Datenhaltung › Personen*.

:::{admonition} **Personen vs. User**
:class: tip

*Personen* sind "Kunden" der DLCDB, z.B. Personen, denen etwas ausgeliehen wird.

*User* oder *Benutzer* der DLCDB sind Menschen, die mit der DLCDB arbeiten und sich an der DLCDB anmelden müssen.
:::

## Devices anlegen

Via Menü *Geräte* (Hauptmenü).

:::{tip}
Auf der Geräte-Übersicht ist rechts oben ein Button *Gerät hinzufügen*.
:::

![Geräte-Übersicht](/_static/devices-index.webp){.sd-card}

## Devices zuordnen

Die DLCDB verwaltet im Grunde nicht nur Devices, sondern vor allem die unterschiedlichen Status (in der DLCDB genannt *Records*), die ein Device in seinem Lebenszyklus durchläuft — siehe [Konzept](../konzept.md).

Als Status oder *Record* stehen zur Verfügung:

1. Lokalisiert → Device ist einem Raum zugeordnet
1. Verliehen → Device ist an eine Person verliehen
1. Nicht auffindbar → Verbleib des Devices ist aktuell nicht klar
1. Entfernt → Device ist z.B. ausgemustert und verschrottet

Jedes Device kann zu einem Zeitpunkt nur einem *Record* zugeordnet sein.

Die DLCDB kann nur sinnvoll Devices verwalten, wenn die entsprechenden *Records* zugewiesen werden. Nach dem Anlegen eines Devices sollte demnach direkt ein *Record* zugeordnet werden.
