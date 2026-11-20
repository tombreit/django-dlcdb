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

Berechtigungen werden **Gruppen** zugewiesen, nicht einzelnen Benutzern: *Einstellungen › Gruppen und Berechtigungen*. Die Seite einer Gruppe listet nur die Berechtigungen, die die DLCDB prüft, geordnet wie ihre Menüs und jede mit dem Menüpunkt, den sie freischaltet. Dort werden auch die Mitglieder und die Mandanten der Gruppe gesetzt. Gruppen und Benutzerkonten selbst legt bis auf Weiteres der Django-Admin an (*Start › Konten*).

### LDAP

Ist die Anmeldung via LDAP eingeschaltet (`AUTH_LDAP` in der `.env`, siehe [Setup](../betrieb/setup.md)), steuern LDAP-Gruppen Anmeldung, Flags und Gruppen:

- **Anmelden** darf, wer Mitglied von `AUTH_LDAP_REQUIRE_GROUP`, `AUTH_LDAP_GROUP_STAFF` oder `AUTH_LDAP_GROUP_SUPERUSERS` ist. Das Benutzerkonto entsteht beim ersten Login.
- **Flags:** Mitglieder von `AUTH_LDAP_GROUP_STAFF` erhalten das Staff-Flag, Mitglieder von `AUTH_LDAP_GROUP_SUPERUSERS` Staff- und Superuser-Flag. Alle Flags, auch *Aktiv*, werden bei jedem Login neu aus LDAP gesetzt: Ein im Django-Admin deaktivierter Benutzer ist nach dem nächsten Login wieder aktiv, solange er in der LDAP-Gruppe ist. Dauerhaft hilft nur, ihn dort zu entfernen.
- **Gruppen:** Die in `AUTH_LDAP_MIRROR_GROUPS` genannten LDAP-Gruppen werden als DLCDB-Gruppen gespiegelt; ihnen werden Berechtigungen und Mandanten zugewiesen. Die Mitgliedschaften in diesen Gruppen werden bei jedem Login aus LDAP übernommen, von Hand vergebene gehen dabei verloren. Andere Gruppen, z.B. in der DLCDB angelegte, bleiben unberührt.
- Eine gespiegelte Gruppe entsteht erst beim ersten Login eines ihrer Mitglieder und fehlt bis dahin in der Mandanten-Übersicht. Soll sie vorher einem Mandanten zugeordnet werden, im Django-Admin eine Gruppe mit exakt dem LDAP-Namen anlegen.

## Navigation

Ein Menüpunkt erscheint nur, wenn eine Gruppe des Benutzers die passende Berechtigung hat; welche das ist, steht auf der Seite der Gruppe unter der Berechtigung. Menüpunkte, die in den Django-Admin führen, erscheinen nur Benutzern mit Staff-Flag, denn nur die erreichen den Admin; auf der Seite *Einstellungen* tragen sie das Abzeichen *Django-Admin*.

Das Zahnrad in der Navigationsleiste öffnet die Seite *Einstellungen*: ihre Einträge nach Bereichen gruppiert, und davon nur die, für die der Benutzer die Berechtigung hat. Hat er keine davon, fehlt das Zahnrad. Das Suchfeld der Seite findet einen Eintrag auch über Begriffe, die nur auf seiner Seite stehen, etwa *Organisation* über „Branding“. Der Schalter *Alle anzeigen* listet auch die Einträge, für die die Berechtigung fehlt (bei Einträgen in den Django-Admin auch das Staff-Flag): ausgegraut, mit Schloss und ohne Link.

## Statuswechsel

Jeder Übergang im Gerätelebenszyklus (siehe [Konzept](../konzept.md)) hat eine eigene Berechtigung; die Seite einer Gruppe listet sie unter *Gerät*. Das Menü *Neuer Zustand* auf der [Geräte-Detailseite](devices.md) bietet einen Übergang genau dann an, wenn er vom aktuellen Status aus zulässig ist **und** der Benutzer die Berechtigung besitzt.

| Aktion | Übergang |
|---|---|
| Bestellung | *(kein Record)* → Bestellt |
| Lokalisieren | *(kein Record)*/Bestellt → Lokalisiert |
| Umziehen | Lokalisiert → Lokalisiert |
| Ausleihen und Zurückgeben | Lokalisiert ↔ Verliehen |
| Nicht auffindbar | Lokalisiert/Verliehen → Nicht auffindbar |
| Gefunden | Nicht auffindbar → Lokalisiert |
| Entfernen | *(kein Record)*/Bestellt/Lokalisiert/Verliehen/Nicht auffindbar → Entfernt |
| Wiederherstellen | Entfernt → Nicht auffindbar |
| Wiedereingliedern | Entfernt → Lokalisiert |

### Frontend oder Django-Admin?

Alle Statuswechsel laufen im Frontend: auf der [Geräte-Detailseite](devices.md) und in der Gerätesuche der [Inventur](inventur.md). Dort zählen allein die Berechtigung des Übergangs und der Zugriff auf den [Mandanten](#mandanten) des Geräts; das Staff-Flag und die Standard-Berechtigungen der Record-Typen (`core.add_removedrecord`, `core.change_lentrecord`, …) spielen keine Rolle. Aus der Gerätesuche der Inventur führt ein Statuswechsel zurück in die Suche, `core.view_device` ist dafür nicht nötig.

Auch die Geräteseite des Django-Admins führt für jeden Statuswechsel in diese Ansichten. Records legt der Django-Admin dafür nicht mehr selbst an: Die *Can add*-Berechtigungen der Record-Typen öffnen nichts mehr; die Seite einer Gruppe listet sie, falls sie sie noch hat, unter den anderen Berechtigungen.

:::{admonition} **Ausmusterung rückgängig machen**
:class: note

*Wiederherstellen* und *Wiedereingliedern* sind nach der Installation **keiner Gruppe zugewiesen**; *Entfernt* ist damit standardmäßig ein Endzustand. Wer diese Wege öffnen möchte, weist die Berechtigungen bewusst einer eng gefassten Gruppe zu.
:::

:::{admonition} **Die Berechtigung gilt für die ganze Aktion**
:class: tip

Eine Berechtigung schaltet nicht nur den Eintrag auf der Geräteseite frei, sondern auch die dahinterliegende Ansicht und deren Geräteauswahl. Wer z.B. nur *Gefunden* besitzt, findet im Menüpunkt *Umziehen* ausschließlich die als *nicht auffindbar* markierten Geräte – und kann genau diese wieder einem Raum zuordnen.
:::

## Mandanten

Ein *Mandant* (im Code *Tenant*) ist eine organisatorische Einheit, die nur ihre eigenen Geräte verwaltet. Der Mandant hängt am **Gerät** (Feld *Mandant*); Records, Ausleihen und Lizenzen erben ihn über ihr Gerät.

Welche Mandanten ein Benutzer sieht, ergibt sich aus seinen **Gruppen**: Ein Mandant gibt den Mitgliedern der ihm zugeordneten Gruppen Zugriff auf seine Geräte (siehe [Mandanten-Übersicht](#mandanten-übersicht)).

- Ein Mandant → der Benutzer sieht nur dessen Geräte.
- Mehrere Mandanten → er sieht die Geräte **aller** dieser Mandanten. Das Benutzermenü zeigt die Zahl der Mandanten, die Geräteliste die Spalte *Mandant*.
- Kein Mandant → er sieht **keine Geräte** und kann keine anlegen. Jede Seite zeigt dann den Hinweis *Keine Ihrer Gruppen gehört zu einem Mandanten, daher sehen Sie keine Geräte.* (nur für Benutzer mit `core.view_device`).
- Das gilt auch für Superuser.

Dateien folgen dem Mandanten ihres Objekts: QR-Codes von Geräten, Anhänge von Records und Import-Dateien liefert die DLCDB nur an Benutzer, die den Mandanten des Geräts bzw. Imports sehen.

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
- das Erfassen gescannter Geräte in der Inventur und die Notizen der laufenden Inventur: Ein Scan erfasst jedes Gerät im Raum, auch eines anderen Mandanten,
- die [REST-API](../betrieb/api.md): Ein API-Token liefert die Geräte aller Mandanten,
- die *Notizen* im Django-Admin (*Datenhaltung › Notizen*),
- der *SAP-Abgleich* der Inventur: Er vergleicht den gesamten Bestand.

### Mandanten-Übersicht

*Einstellungen › Mandanten* zeigt eine Tabelle mit einer Zeile je Gruppe und einer Spalte je Mandant. Ein Haken gibt allen Mitgliedern der Gruppe Zugriff auf die Geräte des Mandanten und wird sofort gespeichert. Neben jeder Gruppe steht die Zahl ihrer aktiven Mitglieder (ein Klick listet sie auf), unter jedem Mandanten die Zahl der Benutzer mit Zugriff (mit LDAP jeweils Stand des letzten Logins). Die Seite eines Mandanten verlinkt seine *Feldhistorie*: wann wer Name, Kontakt-Email oder Gruppen geändert hat, die Haken in der Tabelle eingeschlossen.

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

Die tägliche Arbeit läuft im Frontend. Der Django-Admin (*Django Site-Verwaltung* im Benutzermenü und auf der Seite *Einstellungen* unter *Mehr*) ist nur mit Staff-Flag erreichbar, und auch dort gelten die Gruppen-Berechtigungen. Gebraucht wird er noch für:

- Benutzer und Gruppen anlegen; Benutzer deaktivieren (Aktion *Ausgewählte Benutzer deaktivieren* oder Haken *Aktiv*) oder einzeln *Endgültig löschen* (löscht auch ihre Einträge im Admin-Log). Mit LDAP siehe [LDAP](#ldap).
- die Einträge der Seite *Einstellungen* mit dem Abzeichen *Django-Admin*,
- [Geräte und Importe ohne Mandant](#geräte-und-importe-ohne-mandant) zuordnen,
- erzeugte Reports und den SAP-Import,
- Links (die Ordnungen der Ausleih-Profile), den Kleinkram-Katalog und Anhänge von Records,
- Benachrichtigungen (Status, Vorschau, *Send Now*), den Upload für den Raumabgleich und die vollständige Liste der HR-Sync-Läufe.

Nur Superuser dürfen, unabhängig von Berechtigungen, Stammdaten im Admin endgültig löschen und *aktivieren/deaktivieren* (Soft-Delete, siehe [Model](../betrieb/model.md#softdelete)).

## Beispiel-Gruppen

Vier Gruppen als Ausgangspunkt; jede wird zusätzlich dem passenden Mandanten zugeordnet, damit ihre Mitglieder Geräte sehen.

| Gruppe | Berechtigungen | Ergebnis |
|---|---|---|
| Helpdesk / Ausleihe | `core.view_device`, `core.view_person`, `core.view_lentrecord`, `core.transition_can_lend_device`, `core.transition_can_relocate_device` | Sieht Geräte, Personen und Ausleihen; kann Geräte ausleihen, zurücknehmen und umziehen. |
| Inventur | `core.view_device`, `core.can_inventorize`, `core.change_inventory` | Sieht Geräte, führt die aktive Inventur durch, erreicht Inventuren und SAP-Abgleich (beides *(Admin)*, also mit Staff-Flag). |
| Stammdaten / IT-Beschaffung | `core.view_device`, `core.add_device`, `core.change_device`, `core.view_room`, `core.add_room`, `core.change_room`, `core.view_devicetype`, `core.view_manufacturer`, `core.view_supplier`, `core.transition_can_order_device`, `core.transition_can_locate_device`, `core.transition_can_relocate_device` | Legt Geräte und Räume an, pflegt sie, setzt Geräte auf *Bestellt* bzw. *Lokalisiert* und zieht sie um. |
| Administration | `organization.view_branding`, `organization.change_branding`, `core.view_organizationalunit`, `core.add_organizationalunit`, `core.change_organizationalunit`, `core.delete_organizationalunit`, `core.view_organizationalposition`, `core.add_organizationalposition`, `core.change_organizationalposition`, `core.delete_organizationalposition`, `lending.view_lendingconfiguration`, `lending.change_lendingconfiguration`, `lending.view_lendingprofile`, `lending.add_lendingprofile`, `lending.change_lendingprofile`, `lending.delete_lendingprofile`, `licenses.view_licensesconfiguration`, `licenses.change_licensesconfiguration`, `dataexchange.view_udbsyncconfiguration`, `dataexchange.change_udbsyncconfiguration`, `dataexchange.view_udbsyncrun`, `tenants.view_tenant`, `tenants.add_tenant`, `tenants.change_tenant`, `tenants.delete_tenant`, `journal.view_journalentry`, `journal.delete_journalentry` | Pflegt die Einstellungen, die Ausleih-Profile, Organisationseinheiten und Positionen und die Mandanten und räumt das Journal auf; wird jedem Mandanten zugeordnet. Benutzer, Gruppen und Berechtigungen bleiben Sache des Django-Admins (Staff-Flag). |
