# Berechtigungen

Wer in der DLCDB was sehen und tun darf, ergibt sich aus drei Dingen:

1. der **Stufe** des Benutzerkontos (Benutzer, *Staff*, *Superuser*),
2. den **Berechtigungen** der Gruppen, in denen das Konto Mitglied ist,
3. den **Mandanten**, die sich aus diesen Gruppen ergeben.

Die Einrichtung Schritt für Schritt beschreibt [Erste Schritte](erste_schritte.md).

## Benutzer und Personen

*Benutzer* melden sich an der DLCDB an und arbeiten mit ihr. Sie werden im Django-Admin unter *Start › Konten › Benutzer* verwaltet; mit [LDAP](#ldap) entstehen sie beim ersten Login.

*Personen* sind „Kunden“ der DLCDB, z.B. Menschen, denen ein Gerät ausgeliehen wird. Sie werden unter *Datenhaltung › Personen* gepflegt und haben nichts mit Benutzerkonten oder Berechtigungen zu tun.

## Drei Stufen: Benutzer, Staff, Superuser

| Stufe | Flag am Benutzer | Bedeutung |
|---|---|---|
| Benutzer | – | Arbeitet im Frontend und darf genau das, was die Berechtigungen seiner Gruppen erlauben. |
| Staff | *Mitarbeiter-Status* (`is_staff`) | Zusätzlich Zugang zum [Django-Admin](#django-admin). Auch dort gelten die Gruppen-Berechtigungen. |
| Superuser | *Administrator-Status* (`is_superuser`) | Hat implizit **alle** Berechtigungen, sieht also jeden Menüpunkt und jeden Statuswechsel. Geräte sieht auch ein Superuser nur in seinen [Mandanten](#mandanten). |

`./manage.py createsuperuser` setzt beide Flags, ein Superuser ist also immer auch Staff. Für die tägliche Arbeit ist keines der beiden Flags nötig.

:::{warning}
**Berechtigungen nie als Superuser testen.** Ob eine Gruppe das Richtige freischaltet, zeigt nur ein Testkonto **ohne** Superuser-Flag.
:::

## Gruppen und Berechtigungen

Berechtigungen werden **Gruppen** zugewiesen, nicht einzelnen Benutzern: *Start › Konten › Gruppen*. Benutzer werden unter *Start › Konten › Benutzer* den Gruppen zugeordnet.

Es gibt drei Familien von Berechtigungen:

| Familie | Beispiel | Wofür |
|---|---|---|
| Standard-Berechtigungen pro Model | `core.view_device`, `core.change_room` | Django legt für jedes Model *Can add* / *Can change* / *Can delete* / *Can view* an. Sie schalten Ansichten, Formulare und Menüpunkte frei, im Frontend wie im Django-Admin. |
| Statuswechsel | `core.transition_can_lend_device` | Eine Berechtigung je Übergang im Gerätelebenszyklus, siehe [Statuswechsel](#statuswechsel). |
| Spezielle Berechtigungen | `core.can_inventorize` | Einzelne Prozesse, hier: Inventur durchführen. |

:::{admonition} **Berechtigung unter *Core* finden**
:class: note

Einige Menüpunkte gehören technisch zur App *Core*, obwohl sie in einem anderen Menübereich erscheinen (Proxy-Modelle). Die passende Berechtigung ist dann in der Gruppen-Auswahl unter **Core** gelistet – nicht unter dem gleichnamigen Menü. Beispiel: Der Menüpunkt *Ausleihe* benötigt **Core | lent record | Can view lent record** (`core.view_lentrecord`), nicht eine Berechtigung unter „Lending“.
:::

:::{admonition} **Lesen und Bearbeiten sind getrennte Berechtigungen**
:class: note

Django leitet aus *Can change* kein *Can view* ab. Wer eine Gruppe zum Bearbeiten berechtigt, gibt ihr deshalb auch die passende *Can view*-Berechtigung. Beispiel Lizenzen: Mit `core.change_licencerecord` lässt sich eine Lizenz bearbeiten, die Schaltflächen *Verlauf* und *iCal* benötigen aber `core.view_licencerecord`.
:::

### LDAP

Ist die Anmeldung via LDAP eingeschaltet (`AUTH_LDAP` in der `.env`, siehe [Setup](../betrieb/setup.md)), steuern LDAP-Gruppen Anmeldung, Flags und Gruppen:

- **Anmelden** darf, wer Mitglied von `AUTH_LDAP_REQUIRE_GROUP`, `AUTH_LDAP_GROUP_STAFF` oder `AUTH_LDAP_GROUP_SUPERUSERS` ist. Das Benutzerkonto entsteht beim ersten Login.
- **Flags:** Mitglieder von `AUTH_LDAP_GROUP_STAFF` erhalten das Staff-Flag, Mitglieder von `AUTH_LDAP_GROUP_SUPERUSERS` Staff- und Superuser-Flag. Alle Flags, auch *Aktiv*, werden bei jedem Login neu aus LDAP gesetzt: Ein im Django-Admin deaktivierter Benutzer ist nach dem nächsten Login wieder aktiv, solange er in der LDAP-Gruppe ist. Dauerhaft hilft nur, ihn dort zu entfernen.
- **Gruppen:** Die in `AUTH_LDAP_MIRROR_GROUPS` genannten LDAP-Gruppen werden als DLCDB-Gruppen gespiegelt; ihnen werden Berechtigungen und Mandanten zugewiesen. Die Mitgliedschaften in diesen Gruppen werden bei jedem Login aus LDAP übernommen, von Hand vergebene gehen dabei verloren. Andere Gruppen, z.B. in der DLCDB angelegte, bleiben unberührt.
- Eine gespiegelte Gruppe entsteht erst beim ersten Login eines ihrer Mitglieder und fehlt bis dahin in der Mandanten-Übersicht. Soll sie vorher einem Mandanten zugeordnet werden, im Django-Admin eine Gruppe mit exakt dem LDAP-Namen anlegen.

## Navigation

Die Menüpunkte im Frontend sind an Berechtigungen gebunden: Ein Menüpunkt erscheint nur, wenn eine Gruppe des Benutzers die genannte Berechtigung besitzt – in der Regel die *view*-Berechtigung der verlinkten Ansicht. Steht mehr als eine Berechtigung in der Zeile, genügt **eine** davon.

Mit *(Admin)* markierte Menüpunkte öffnen den Django-Admin. Die Menüprüfung fragt nur die Berechtigung ab; zum Öffnen braucht der Benutzer zusätzlich das Staff-Flag. Diese Berechtigungen deshalb nur Gruppen geben, deren Mitglieder Staff sind.

<!-- Diese Tabelle spiegelt die "required_permission"-Werte aus den
     dlcdb/*/navigation.py-Dateien wider; *(Admin)* markiert Einträge,
     deren "url" auf "admin:..." zeigt. Bei Änderungen an den Menüs
     (Hinzufügen/Entfernen von Navigationseinträgen) hier nachziehen.
     Invariante: Die "required_permission" eines Menüeintrags ist immer
     die Lese-Berechtigung der verlinkten Ansicht -- ein sichtbarer
     Menüpunkt kann so nie in einer Fehlermeldung enden. -->

| Menüpunkt (Bereich) | Berechtigung (Django-Admin-Anzeige) | codename |
|---|---|---|
| Ausleihe (Hauptmenü) | Core \| lent record \| Can view lent record | `core.view_lentrecord` |
| Geräte (Hauptmenü) | Core \| device \| Can view device | `core.view_device` |
| Umziehen (Hauptmenü) | Core \| record \| eine der drei Bewegungs-Berechtigungen | `core.transition_can_locate_device`, `core.transition_can_relocate_device` oder `core.transition_can_find_device` |
| Inventarisieren (Hauptmenü, nur bei aktiver Inventur) | Core \| … \| Can inventorize | `core.can_inventorize` |
| Kleinkram (Hauptmenü), weitere Berechtigungen siehe [Kleinkram](kleinkram.md) | Smallstuff \| assigned thing \| Can view assigned thing | `smallstuff.view_assignedthing` |
| Lizenzen (Hauptmenü) | Core \| licence record \| Can view licence record | `core.view_licencerecord` |
| Datenhaltung › Räume | Core \| room \| Can view room | `core.view_room` |
| Datenhaltung › Hersteller | Core \| manufacturer \| Can view manufacturer | `core.view_manufacturer` |
| Datenhaltung › Zulieferer | Core \| supplier \| Can view supplier | `core.view_supplier` |
| Datenhaltung › Geräteklassen | Core \| device type \| Can view device type | `core.view_devicetype` |
| Datenhaltung › Personen | Core \| person \| Can view person | `core.view_person` |
| Datenhaltung › Records | Core \| record \| Can view record | `core.view_record` |
| Datenhaltung › Entfernt-Records *(Admin)* | Core \| record \| Can view record | `core.view_record` |
| Datenhaltung › Inventuren *(Admin)* | Core \| inventory \| Can change inventory | `core.change_inventory` |
| Datenhaltung › Notizen *(Admin)* | Core \| note \| Can view note | `core.view_note` |
| Prozesse › Bulk Import | Data Exchange \| importer list \| Can view importer list | `dataexchange.view_importerlist` |
| Prozesse › Bulk Ausmusterung *(Admin)* | Data Exchange \| remover list \| Can view remover list | `dataexchange.view_removerlist` |
| Prozesse › Inventarisieren (nur bei aktiver Inventur) | Core \| … \| Can inventorize | `core.can_inventorize` |
| Prozesse › SAP-Abgleich (nur bei aktiver Inventur) *(Admin)* | Core \| inventory \| Can change inventory | `core.change_inventory` |
| Einstellungen › Mandanten | Tenants \| tenant \| Can view tenant | `tenants.view_tenant` |
| Einstellungen › Ausleihe Konfiguration *(Admin)* | Lending \| lending configuration \| Can view lending configuration | `lending.view_lendingconfiguration` |
| Einstellungen › Ausleih-Profile *(Admin)* | Lending \| lending profile \| Can view lending profile | `lending.view_lendingprofile` |
| Einstellungen › Lizenzmodul Konfiguration *(Admin)* | Licenses \| licenses configuration \| Can view licenses configuration | `licenses.view_licensesconfiguration` |
| Einstellungen › Branding *(Admin)* | Organization \| branding \| Can view branding | `organization.view_branding` |
| Einstellungen › HR-API-Sync-Konfiguration *(Admin)* | Data Exchange \| HR API Sync Configuration \| Can view HR API Sync Configuration | `dataexchange.view_udbsyncconfiguration` |
| Einstellungen › Journal | Journal \| journal entry \| Can view journal entry | `journal.view_journalentry` |

## Statuswechsel

Jeder Übergang im Gerätelebenszyklus (siehe [Konzept](../konzept.md)) hat eine eigene Berechtigung. Das Menü *Neuer Zustand* auf der [Geräte-Detailseite](devices.md) bietet einen Übergang genau dann an, wenn er vom aktuellen Status aus zulässig ist **und** der Benutzer die Berechtigung besitzt. Alle neun sind in der Gruppen-Auswahl unter **Core | record** gelistet.

| Aktion | Übergang | Berechtigung (Django-Admin-Anzeige) | codename |
|---|---|---|---|
| Bestellung | *(kein Record)* → Bestellt | Core \| record \| Transition: Can record a device as ordered | `core.transition_can_order_device` |
| Lokalisieren | *(kein Record)*/Bestellt → Lokalisiert | Core \| record \| Transition: Can localise a device for the first time | `core.transition_can_locate_device` |
| Umziehen | Lokalisiert → Lokalisiert | Core \| record \| Transition: Can move a device to another room | `core.transition_can_relocate_device` |
| Ausleihen und Zurückgeben | Lokalisiert ↔ Verliehen | Core \| record \| Transition: Can lend a device and take it back | `core.transition_can_lend_device` |
| Nicht auffindbar | Lokalisiert/Verliehen → Nicht auffindbar | Core \| record \| Transition: Can mark a device as not locatable | `core.transition_can_lose_device` |
| Gefunden | Nicht auffindbar → Lokalisiert | Core \| record \| Transition: Can mark a lost device as found | `core.transition_can_find_device` |
| Entfernen | Lokalisiert/Verliehen/Nicht auffindbar → Entfernt | Core \| record \| Transition: Can remove (decommission) a device | `core.transition_can_remove_device` |
| Wiederherstellen | Entfernt → Nicht auffindbar | Core \| record \| Transition: Can restore a removed device to not-locatable | `core.transition_can_restore_device` |
| Wiedereingliedern | Entfernt → Lokalisiert | Core \| record \| Transition: Can recover a removed device into a room | `core.transition_can_recover_device` |

### Frontend oder Django-Admin?

Die Berechtigung entscheidet, **ob** ein Statuswechsel angeboten wird. **Wo** er ausgeführt wird, hängt vom Übergang ab:

| Übergang | Ausführung | benötigt zusätzlich |
|---|---|---|
| Bestellung, Lokalisieren, Umziehen, Gefunden, Ausleihen, Zurückgeben | Frontend | nichts |
| Nicht auffindbar, Entfernen, Wiederherstellen, Wiedereingliedern | Django-Admin-Formular (Menüeintrag mit ↗-Symbol) | *Staff*-Flag **und** die *Can add*-Berechtigung des geschriebenen Records: `core.add_lostrecord`, `core.add_removedrecord` bzw. `core.add_inroomrecord` (Wiedereingliedern) |

Ohne Staff-Flag erscheinen die Admin-gestützten Einträge gar nicht erst. Die übrigen Standard-Berechtigungen der Record-Typen (`core.add_lentrecord`, `core.change_lentrecord`, …) steuern keine Statuswechsel; im Frontend zählen allein die `transition_*`-Berechtigungen.

:::{admonition} **Ausmusterung rückgängig machen**
:class: note

`transition_can_restore_device` und `transition_can_recover_device` sind nach der Installation **keiner Gruppe zugewiesen**; *Entfernt* ist damit standardmäßig ein Endzustand. Wer diese Wege öffnen möchte, weist die Berechtigungen bewusst einer eng gefassten Gruppe mit Staff-Flag zu.
:::

:::{admonition} **Die Berechtigung gilt für die ganze Aktion**
:class: tip

Eine Berechtigung schaltet nicht nur den Eintrag auf der Geräteseite frei, sondern auch die dahinterliegende Ansicht und deren Geräteauswahl. Wer z.B. nur `core.transition_can_find_device` besitzt, findet im Menüpunkt *Umziehen* ausschließlich die als *nicht auffindbar* markierten Geräte – und kann genau diese wieder einem Raum zuordnen.
:::

## Mandanten

Ein *Mandant* (im Code *Tenant*) ist eine organisatorische Einheit, die nur ihre eigenen Geräte verwaltet. Der Mandant hängt am **Gerät** (Feld *Mandant*); Records, Ausleihen und Lizenzen erben ihn über ihr Gerät.

Welche Mandanten ein Benutzer sieht, ergibt sich aus seinen **Gruppen**: Ein Mandant gibt den Mitgliedern der ihm zugeordneten Gruppen Zugriff auf seine Geräte (siehe [Mandanten-Übersicht](#mandanten-übersicht)).

- Ein Mandant → der Benutzer sieht nur dessen Geräte.
- Mehrere Mandanten → er sieht die Geräte **aller** dieser Mandanten. Das Benutzermenü zeigt die Zahl der Mandanten, die Geräteliste die Spalte *Mandant*.
- Kein Mandant → er sieht **keine Geräte** und kann keine anlegen. Jede Seite zeigt dann den Hinweis *Keine Ihrer Gruppen gehört zu einem Mandanten, daher sehen Sie keine Geräte.* (nur für Benutzer mit `core.view_device`).
- Das gilt auch für Superuser.

Beim Anlegen und Importieren ist ein Mandant Pflicht. Das Feld *Mandant* eines Geräts, einer Lizenz oder eines Imports bietet nur die eigenen Mandanten an; bei genau einem ist er vorausgewählt. Wer mehrere Mandanten sieht und `core.change_device` besitzt, kann ein Gerät zwischen ihnen verschieben: auf der Geräte-Detailseite oder, für mehrere Geräte, mit der Aktion *Ausgewählte Geräte umziehen* im Geräte-Admin.

**Alle Mandanten sehen.** Eine Gruppe, die alle Mandanten sehen soll (z.B. Administratoren, IT, Revision), wird **jedem** Mandanten zugeordnet, auch jedem neu angelegten. In der Mandanten-Übersicht ist das eine Zeile mit Haken in jeder Spalte; eine Lücke darin ist ein vergessener Mandant.

Mandanten vergeben **keine** Berechtigungen: Was ein Benutzer tun darf, bestimmen allein seine Gruppen, der Mandant nur, welche Geräte er dabei sieht. Üblich ist eine Gruppe pro Mandant und Rolle.

:::{warning}
**Berechtigungen gelten in allen Mandanten eines Benutzers.** Wer über die Gruppe *ops-a* Geräte in Mandant A bearbeiten darf und über *audit-b* Mandant B nur ansehen soll, kann trotzdem auch die Geräte von B bearbeiten. Unterschiedliche Rollen je Mandant lassen sich nicht abbilden; dafür getrennte Benutzerkonten verwenden.
:::

:::{warning}
**`tenants.change_tenant` entscheidet über die Sichtbarkeit – auch über die eigene.** Wer diese Berechtigung besitzt, kann die eigene Gruppe jedem Mandanten zuordnen und so dessen Geräte sehen. Außerdem setzt er die Kontakt-Email eines Mandanten, an die die [Erinnerungen an überfällige Ausleihen](notifications.md) gehen, mit den Namen der Ausleihenden. Die Berechtigung gehört deshalb wie die Gruppenverwaltung zu den Administrations-Berechtigungen.
:::

Nicht auf die eigenen Mandanten eingeschränkt sind:

- die *Devices*-Übersicht der Inventur-App, wenn bei der Inventur *Geräte-Suche ist Tenant-spezifisch* ausgeschaltet ist (siehe [Inventur](inventur.md)),
- die [REST-API](../betrieb/api.md): Ein API-Token liefert die Geräte aller Mandanten,
- die *Notizen* im Django-Admin (*Datenhaltung › Notizen*),
- der *SAP-Abgleich* der Inventur: Er vergleicht den gesamten Bestand.

### Mandanten-Übersicht

*Einstellungen › Mandanten* zeigt eine Tabelle mit einer Zeile je Gruppe und einer Spalte je Mandant. Ein Haken gibt allen Mitgliedern der Gruppe Zugriff auf die Geräte des Mandanten und wird sofort gespeichert. Neben jeder Gruppe steht die Zahl ihrer aktiven Mitglieder (ein Klick listet sie auf), unter jedem Mandanten die Zahl der Benutzer mit Zugriff (mit LDAP jeweils Stand des letzten Logins).

- `tenants.view_tenant`: die Übersicht ansehen
- `tenants.change_tenant`: Haken setzen, Mandanten umbenennen, Kontakt-Email setzen
- `tenants.add_tenant`: Mandanten anlegen
- `tenants.delete_tenant`: Mandanten ohne Geräte und Importe löschen (zusammen mit `tenants.change_tenant`, Schaltfläche auf der Detailseite)

Jede Änderung, auch an den Haken, steht in der Änderungshistorie des Mandanten im Django-Admin. Einen Mandanten mit Geräten oder Importen kann man nicht löschen: Die Geräte zuerst einem anderen Mandanten zuordnen; Importe lassen sich im Django-Admin löschen.

### Geräte und Importe ohne Mandant

Ältere Geräte und Importe ohne Mandant erscheinen in keiner Liste, auch nicht für Superuser. Solange es sie gibt, zeigt die DLCDB allen, die sie zuordnen dürfen, auf jeder Seite den Hinweis *N Geräte ohne Mandant!* bzw. *N Importe ohne Mandant!*. Zum Zuordnen:

1. Dem Link *Mandant zuordnen?* folgen (Django-Admin, *Start › Mandanten › Tenants*).
2. Den Ziel-Mandanten auswählen und die Aktion *Geräte und Importe ohne Mandant zuordnen* ausführen.
3. Die folgende Seite listet alle Geräte und Importe ohne Mandant. Was zu einem anderen Mandanten gehört, abwählen und bestätigen; für das Übrige die Schritte mit dessen Mandant wiederholen.

Die Aktion benötigt das Staff-Flag, `tenants.change_tenant` sowie `core.change_device` für Geräte bzw. `dataexchange.change_importerlist` für Importe; die Seite zeigt alles, was der Benutzer ändern darf, unabhängig von den eigenen Mandanten. Den Mandanten eines Imports nicht im Import-Formular des Django-Admins ändern: Speichern dort führt den Import erneut aus.

Reichen die Angaben auf der Bestätigungsseite nicht, alle Geräte einem **Zwischen-Mandanten** *Unassigned* (der IT-Gruppe zugeordnet) zuweisen und dann auf ihren Detailseiten dem richtigen Mandanten zuordnen. Den leeren Zwischen-Mandanten danach löschen.

## Django-Admin

Die tägliche Arbeit läuft im Frontend. Der Django-Admin (*Django Site-Verwaltung* im Benutzermenü) ist nur mit Staff-Flag erreichbar, und auch dort gelten die Gruppen-Berechtigungen. Gebraucht wird er noch für:

- Benutzer und Gruppen anlegen und Berechtigungen vergeben; Benutzer deaktivieren (Aktion *Ausgewählte Benutzer deaktivieren* oder Haken *Aktiv*) oder einzeln *Endgültig löschen* (löscht auch ihre Einträge im Admin-Log). Mit LDAP siehe [LDAP](#ldap).
- die mit *(Admin)* markierten [Menüpunkte](#navigation) und die vier [Admin-gestützten Statuswechsel](#frontend-oder-django-admin),
- [Geräte und Importe ohne Mandant](#geräte-und-importe-ohne-mandant) zuordnen,
- die Änderungshistorie eines Mandanten, erzeugte Reports und den SAP-Import.

Nur Superuser dürfen, unabhängig von Berechtigungen:

- Stammdaten im Admin endgültig löschen und *aktivieren/deaktivieren* (Soft-Delete, siehe [Model](../betrieb/model.md#softdelete)),
- im Geräte-Admin die Aktion *Wiederherstellung von REMOVED auf LOST* ausführen.

## Beispiel-Gruppen

Drei Gruppen als Ausgangspunkt; jede wird zusätzlich dem passenden Mandanten zugeordnet, damit ihre Mitglieder Geräte sehen.

| Gruppe | Berechtigungen | Ergebnis |
|---|---|---|
| Helpdesk / Ausleihe | `core.view_device`, `core.view_person`, `core.view_lentrecord`, `core.transition_can_lend_device`, `core.transition_can_relocate_device` | Sieht Geräte, Personen und Ausleihen; kann Geräte ausleihen, zurücknehmen und umziehen. |
| Inventur | `core.view_device`, `core.can_inventorize`, `core.change_inventory` | Sieht Geräte, führt die aktive Inventur durch, erreicht Inventuren und SAP-Abgleich (beides *(Admin)*, also mit Staff-Flag). |
| Stammdaten / IT-Beschaffung | `core.view_device`, `core.add_device`, `core.change_device`, `core.view_room`, `core.add_room`, `core.change_room`, `core.view_devicetype`, `core.view_manufacturer`, `core.view_supplier`, `core.transition_can_order_device`, `core.transition_can_locate_device`, `core.transition_can_relocate_device` | Legt Geräte und Räume an, pflegt sie, setzt Geräte auf *Bestellt* bzw. *Lokalisiert* und zieht sie um. |
