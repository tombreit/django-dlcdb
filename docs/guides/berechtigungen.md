# Berechtigungen

Wer in der DLCDB was sehen und tun darf, ergibt sich aus drei Dingen:

1. den **Stufen** des Benutzerkontos (normaler Benutzer, *Staff*, *Superuser*),
2. den **Berechtigungen** der Gruppen, in denen das Konto Mitglied ist,
3. dem **Tenant**, der sich aus diesen Gruppen ergibt.

Diese Seite erklärt, wie die drei zusammenhängen und wo welche Einstellung vorgenommen wird. Die Einrichtung selbst ist Schritt für Schritt unter [Erste Schritte](erste_schritte.md) beschrieben.

## Benutzer und Personen

*Benutzer* (oder *User*) sind Menschen, die sich an der DLCDB anmelden und mit ihr arbeiten. Sie werden unter *Start › Accounts › Benutzer* verwaltet; bei LDAP-Anmeldung entstehen sie automatisch beim ersten Login.

*Personen* sind „Kunden“ der DLCDB, z.B. Menschen, denen ein Gerät ausgeliehen wird. Sie werden unter *Datenhaltung › Personen* gepflegt und haben nichts mit Benutzerkonten oder Berechtigungen zu tun.

## Drei Stufen: Benutzer, Staff, Superuser

| Stufe | Flag am Benutzer | Bedeutung |
|---|---|---|
| Benutzer | – | Arbeitet im Frontend. Sieht und darf genau das, was die Berechtigungen seiner Gruppen erlauben. |
| Staff | *Mitarbeiter-Status* (`is_staff`) | Zusätzlich Zugang zur Django-Admin-Oberfläche (Eintrag *Django Site-Verwaltung* im Benutzermenü). Auch dort gelten die Gruppen-Berechtigungen. Einige Statuswechsel öffnen ein Admin-Formular und sind deshalb nur mit diesem Flag erreichbar (siehe [Frontend oder Django-Admin?](#frontend-oder-django-admin)). |
| Superuser | *Administrator-Status* (`is_superuser`) | Hat implizit **alle** Berechtigungen: sieht alle Menüpunkte und alle Statuswechsel. Geräte sieht auch ein Superuser nur in den Tenants seiner Gruppen (siehe [Tenants](#tenants)). Nur Superuser dürfen im Admin löschen, Stammdaten aktivieren/deaktivieren und die Admin-Aktion *Restore devices from REMOVED to LOST* ausführen. |

- `./manage.py createsuperuser` setzt beide Flags. Ein Superuser ist damit immer auch Staff.
- Bei LDAP-Anmeldung erhalten Mitglieder der in `AUTH_LDAP_GROUP_SUPERUSERS` (`.env`) genannten LDAP-Gruppe **beide** Flags.
- Für die tägliche Arbeit sind weder Staff noch Superuser nötig: Alle Alltagsansichten laufen im Frontend und werden allein über Gruppen-Berechtigungen freigeschaltet.

:::{warning}
**Berechtigungen nie als Superuser testen.** Ein Superuser sieht jeden Menüpunkt und jeden Statuswechsel – auch ohne die zugehörige Berechtigung. Ob eine Gruppe wirklich das Richtige freischaltet, zeigt nur ein Testkonto **ohne** Superuser-Flag.
:::

## Gruppen und Berechtigungen

Berechtigungen werden **Gruppen** zugewiesen, nicht einzelnen Benutzern: *Start › Authentifizierung und Autorisierung › Gruppen*. Benutzer werden dann unter *Start › Accounts › Benutzer* den Gruppen zugeordnet.

Es gibt drei Familien von Berechtigungen:

| Familie | Beispiel | Wofür |
|---|---|---|
| Standard-Berechtigungen pro Model | `core.view_device`, `core.change_room` | Django legt für jedes Model *Can add* / *Can change* / *Can delete* / *Can view* an. Sie schalten Ansichten, Formulare und Menüpunkte im Frontend frei – und dieselben Module im Django-Admin. |
| Statuswechsel | `core.transition_can_lend_device` | Neun eigene Berechtigungen, eine je Übergang im Gerätelebenszyklus. In der Gruppen-Auswahl unter **Core \| record \| Transition: …** gelistet. Siehe [Statuswechsel](#statuswechsel). |
| Spezielle Berechtigungen | `core.can_inventorize` | Einzelne Prozesse, hier: Inventur durchführen. |

:::{admonition} **Berechtigung unter *Core* finden**
:class: note

Einige Menüpunkte gehören technisch zur App *Core*, obwohl sie in einem anderen Menübereich erscheinen (Proxy-Modelle). Die passende Berechtigung ist dann in der Gruppen-Auswahl unter **Core** gelistet – nicht unter dem gleichnamigen Menü. Beispiel: Der Menüpunkt *Ausleihe* benötigt die Berechtigung **Core | lent record | Can view lent record** (`core.view_lentrecord`), nicht eine Berechtigung unter „Lending“.
:::

:::{admonition} **Lesen und Bearbeiten sind getrennte Berechtigungen**
:class: note

Django leitet aus *Can change* kein *Can view* ab. Wer eine Gruppe zum Bearbeiten berechtigt, sollte ihr deshalb immer auch die passende *Can view*-Berechtigung geben. Beispiel Lizenzen: Mit `core.change_licencerecord` lässt sich eine Lizenz bearbeiten, aber die Schaltflächen *Verlauf* und *iCal* auf dem Bearbeitungsformular benötigen `core.view_licencerecord`.
:::

:::{admonition} **LDAP**
:class: note

Ist die Anmeldung via LDAP konfiguriert, werden die in `AUTH_LDAP_MIRROR_GROUPS` (`.env`) genannten LDAP-Gruppen als DLCDB-Gruppen gespiegelt. Berechtigungen und Tenants werden dann diesen **gespiegelten Gruppen** zugewiesen. Die Mitgliedschaften in diesen gespiegelten Gruppen werden bei jeder Anmeldung aus LDAP übernommen; von Hand vergebene Mitgliedschaften in ihnen gehen dabei verloren. Mitgliedschaften in Gruppen, die nicht in `AUTH_LDAP_MIRROR_GROUPS` stehen (z.B. eine in der DLCDB angelegte Gruppe), bleiben unberührt.
:::

## Navigation

Die Menüpunkte im Frontend sind an Berechtigungen gebunden: Ein Menüpunkt erscheint für einen Benutzer nur dann, wenn eine seiner Gruppen die in der Tabelle genannte Berechtigung besitzt – in der Regel die *view*-Berechtigung des zugrundeliegenden Models. Ein sichtbarer Menüpunkt kann so nie in einer Fehlermeldung enden.

<!-- Diese Tabelle spiegelt die "required_permission"-Werte aus den
     dlcdb/*/navigation.py-Dateien wider. Bei Änderungen an den Menüs
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
| Kleinkram (Hauptmenü) | Smallstuff \| assigned thing \| Can view assigned thing | `smallstuff.view_assignedthing` [^kleinkram] |
| Lizenzen (Hauptmenü) | Core \| licence record \| Can view licence record | `core.view_licencerecord` |
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
| Prozesse › Inventarisieren (nur bei aktiver Inventur) | Core \| … \| Can inventorize | `core.can_inventorize` |
| Prozesse › SAP-Abgleich (nur bei aktiver Inventur) | Core \| inventory \| Can change inventory | `core.change_inventory` |
| Einstellungen › Ausleihe Konfiguration | Lending \| lending configuration \| Can view lending configuration | `lending.view_lendingconfiguration` |
| Einstellungen › Ausleih-Profile | Lending \| lending profile \| Can view lending profile | `lending.view_lendingprofile` |
| Einstellungen › Lizenzmodul Konfiguration | Licenses \| licenses configuration \| Can view licenses configuration | `licenses.view_licensesconfiguration` |
| Einstellungen › Branding | Organization \| branding \| Can view branding | `organization.view_branding` |
| Einstellungen › HR-API-Sync-Konfiguration | Data Exchange \| HR API Sync Configuration \| Can view HR API Sync Configuration | `dataexchange.view_udbsyncconfiguration` |

[^kleinkram]: `smallstuff.view_assignedthing` öffnet die Ansicht. Zum Ausgeben eines Gegenstands wird zusätzlich `smallstuff.add_assignedthing` benötigt, zum Zurücknehmen `smallstuff.change_assignedthing`.

Steht bei einem Menüpunkt mehr als eine Berechtigung, genügt **eine** davon. Superuser sehen alle Menüpunkte.

:::{admonition} **Menüpunkte, die in den Django-Admin führen**
:class: note

Die Einträge *Entfernt-Records*, *Inventuren*, *Notizen*, *Bulk Ausmusterung*, *SAP-Abgleich* und alle Einträge unter *Einstellungen* öffnen eine Django-Admin-Ansicht. Die Menüprüfung fragt nur die Berechtigung ab; zum Öffnen braucht der Benutzer zusätzlich das **Staff-Flag**, sonst landet er auf der Admin-Anmeldeseite. Diese Berechtigungen deshalb nur Gruppen geben, deren Mitglieder Staff sind.
:::

## Statuswechsel

Welche Statuswechsel (*Records*) einem Benutzer für ein Gerät angeboten werden, ist an Berechtigungen gebunden. Jeder Übergang im Gerätelebenszyklus (siehe [Konzept](../konzept.md)) hat eine eigene Berechtigung; angeboten wird ein Übergang genau dann, wenn er vom aktuellen Status aus überhaupt zulässig ist **und** der Benutzer die zugehörige Berechtigung besitzt.

Damit entscheidet die Rechtevergabe – nicht der Programmcode –, welche Aktionen eine Gruppe im Alltag sieht. Alle neun Berechtigungen sind in der Gruppen-Auswahl unter **Core | record** gelistet.

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

Die Aktion erscheint auf der Geräte-Detailseite im Menü *Neuer Zustand* (siehe [Geräte](devices.md)).

### Frontend oder Django-Admin?

Die Berechtigung entscheidet, **ob** ein Statuswechsel angeboten wird. **Wo** er ausgeführt wird, hängt vom Übergang ab: Ein Teil läuft vollständig im Frontend, der Rest öffnet noch ein Formular des Django-Admins.

| Übergang | Ausführung | benötigt zusätzlich |
|---|---|---|
| Bestellung, Lokalisieren, Umziehen, Gefunden, Ausleihen, Zurückgeben | Frontend | nichts – die Transition-Berechtigung genügt |
| Nicht auffindbar, Entfernen, Wiederherstellen, Wiedereingliedern | Django-Admin-Formular (Menüeintrag mit ↗-Symbol) | *Staff*-Flag **und** die *Can add*-Berechtigung des geschriebenen Records: `core.add_lostrecord`, `core.add_removedrecord` bzw. `core.add_inroomrecord` (Wiedereingliedern) |

Ohne Staff-Flag werden die Admin-gestützten Einträge im Menü *Neuer Zustand* gar nicht erst angezeigt. Auch die CSV-Bulk-Ausmusterung (*Prozesse › Bulk Ausmusterung*, siehe [Ausmustern](ausmustern.md)) läuft im Django-Admin.

:::{admonition} **Die alten *Can add*-Berechtigungen der Records**
:class: note

Die Standard-Berechtigungen der Record-Typen (`core.add_inroomrecord`, `core.add_lentrecord`, `core.change_lentrecord`, …) steuern **keine** Statuswechsel mehr. Sie werden nur noch von Django selbst für die oben genannten Admin-Formulare geprüft. Für alle Frontend-Abläufe sind ausschließlich die `transition_*`-Berechtigungen maßgeblich.
:::

:::{admonition} **Ausmusterung rückgängig machen**
:class: note

`transition_can_restore_device` und `transition_can_recover_device` sind nach der Installation **keiner Gruppe zugewiesen**. Ein ausgemustertes Gerät ist damit standardmäßig ein Endpunkt. Wer diese Wege öffnen möchte, weist die Berechtigungen bewusst zu – üblicherweise nur einer eng gefassten Gruppe, die zudem das Staff-Flag hat (siehe oben).

Unabhängig davon steht Superusern im Device-Admin die Massen-Aktion *Restore devices from REMOVED to LOST* zur Verfügung. Sie ist an das Superuser-Flag gebunden, nicht an eine Berechtigung.
:::

:::{admonition} **Die Berechtigung gilt für die ganze Aktion**
:class: tip

Eine Berechtigung schaltet nicht nur den Eintrag auf der Geräteseite frei, sondern auch die dahinterliegende Ansicht und deren Geräteauswahl. Wer z.B. nur `core.transition_can_find_device` besitzt, findet im Menüpunkt *Umziehen* ausschließlich die als *nicht auffindbar* markierten Geräte – und kann genau diese wieder einem Raum zuordnen.
:::

## Tenants

Ein *Tenant* (Mandant) ist eine organisatorische Einheit, die die DLCDB nutzt und nur ihre eigenen Geräte verwaltet. Der Tenant hängt am **Gerät** (*Datenhaltung › Geräte › Mandant*); Records, Ausleihen und Lizenzen erben ihn über ihr Gerät.

**Zuordnung zum Benutzer.** Ein Tenant besitzt eine oder mehrere **Gruppen** (*Start › Tenants › Tenant › Gruppen*). Der Tenant eines Benutzers ergibt sich aus dessen Gruppenmitgliedschaften:

- Genau ein Tenant passt zu den Gruppen des Benutzers → der Benutzer arbeitet in diesem Tenant und sieht nur dessen Geräte.
- Mehrere Tenants passen → der Benutzer sieht die Geräte **aller** dieser Tenants. Die Navigation zeigt die Zahl der Tenants, die Geräteliste die Spalte *Mandant*.
- Kein Tenant passt → der Benutzer sieht **keine Geräte** und kann keine anlegen; jede Seite zeigt den Hinweis *None of your groups belongs to a tenant, so you see no devices.* (nur für Benutzer mit `core.view_device`).
- Superuser bilden **keine** Ausnahme: Auch sie sehen nur die Tenants ihrer Gruppen. Ein Superuser ohne passende Gruppe sieht keine Geräte.

Beim Anlegen eines Geräts, einer Lizenz oder eines Imports bietet das Feld *Tenant* nur die eigenen Tenants an; mit genau einem Tenant ist er vorausgewählt, mit mehreren muss einer gewählt werden. Wer mehrere Tenants sieht und `core.change_device` besitzt, kann ein Gerät zwischen diesen Tenants verschieben: auf der Geräte-Detailseite (Feld *Tenant*) oder für mehrere Geräte über die Admin-Aktion *Relocate* (siehe [Umziehen](umziehen.md)).

**Alle Tenants sehen.** Eine eigene „Alle Tenants“-Stufe gibt es nicht: Eine Gruppe, die alle Tenants sehen soll (z.B. Administratoren, IT, Einkauf, Revision), wird **jedem** Tenant zugeordnet – auch jedem neu angelegten. Wird das bei einem neuen Tenant vergessen, sieht die Gruppe ihn schlicht nicht. Wer *wen* sieht, steht damit immer vollständig in der Gruppen-Liste des Tenants (Spalte *Groups* in der Tenant-Übersicht).

Tenants vergeben **keine** Berechtigungen. Was ein Benutzer tun darf, bestimmen ausschließlich seine Gruppen; der Tenant bestimmt nur, welche Geräte er dabei sieht. Üblicherweise verwendet man dieselben Gruppen für beides: eine Gruppe pro Tenant und Rolle, mit den passenden Berechtigungen, dem Tenant zugeordnet.

:::{warning}
**Berechtigungen gelten in allen Tenants eines Benutzers.** Wer über die Gruppe *ops-a* Geräte in Tenant A bearbeiten darf und über *audit-b* Tenant B nur ansehen soll, kann trotzdem auch die Geräte von B bearbeiten. Unterschiedliche Rollen je Tenant lassen sich nicht abbilden; dafür getrennte Benutzerkonten verwenden.
:::

Nicht auf den Tenant eingeschränkt sind:

- die *Devices*-Übersicht der Inventur-App, wenn bei der Inventur *Device search tenant aware* ausgeschaltet ist (siehe [Inventur](inventur.md)),
- die [REST-API](../betrieb/api.md): Ein API-Token liefert die Geräte aller Tenants,
- die *Notizen* im Django-Admin (*Datenhaltung › Notizen*).

### Geräte ohne Tenant

Jedes Gerät braucht einen Tenant: Auch Superuser müssen beim Anlegen und beim Import einen auswählen. Ältere Geräte ohne Tenant erscheinen in keiner Liste, auch nicht für Superuser; solange es sie gibt, zeigt die DLCDB auf jeder Seite den Hinweis *N devices without tenant!*. Zum Zuordnen:

1. Dem Link *Assign a tenant?* folgen (*Start › Tenants › Tenant*).
2. Den Ziel-Tenant auswählen und die Aktion *Assign devices without tenant* ausführen.
3. Die folgende Seite listet alle Geräte ohne Tenant. Geräte, die zu einem anderen Tenant gehören, abwählen und bestätigen. Für die übrigen Geräte die Schritte mit deren Tenant wiederholen.

Die Aktion benötigt die Berechtigungen `tenants.change_tenant` **und** `core.change_device`; sie listet die Geräte unabhängig von den eigenen Tenants.

Reichen die Angaben auf der Bestätigungsseite nicht für die Entscheidung, hilft ein **Zwischen-Tenant**: einen Tenant *Unassigned* anlegen und der IT-Gruppe zuordnen, alle Geräte ohne Tenant per Aktion dorthin verschieben, dann jedes Gerät auf seiner Detailseite (Feld *Tenant*) dem richtigen Tenant zuordnen. Ist *Unassigned* leer, kann er gelöscht werden.

Ein Tenant, dem noch Geräte zugeordnet sind, lässt sich nicht löschen. Seine Geräte zuerst einem anderen Tenant zuordnen.

## Rolle des Django-Admins

Die tägliche Arbeit – Geräte, Räume, Personen, Stammdaten, Ausleihe, Umzug, Inventur, Lizenzen, Import – läuft vollständig im Frontend. Der Django-Admin (*Django Site-Verwaltung* im Benutzermenü, nur mit Staff-Flag) wird noch für Folgendes benötigt:

- Benutzer, Gruppen, Berechtigungen und Tenants anlegen und zuordnen
- Geräte ohne Tenant einem Tenant zuordnen (siehe [Geräte ohne Tenant](#geräte-ohne-tenant))
- die vier Admin-gestützten Statuswechsel (siehe [Frontend oder Django-Admin?](#frontend-oder-django-admin))
- Massen-Aktion *Restore devices from REMOVED to LOST* (nur Superuser)
- Stammdaten *aktivieren/deaktivieren* (Soft-Delete, nur Superuser) und endgültig löschen (nur Superuser)
- die feldgenaue Änderungs-*History* eines Geräts
- Bulk Ausmusterung, Entfernt-Records, Inventuren, Notizen, SAP-Abgleich, erzeugte Reports
- alle Einträge unter *Einstellungen* (Ausleihe-Konfiguration, Ausleih-Profile, Lizenzmodul-Konfiguration, Branding, HR-API-Sync-Konfiguration)

Die *Fallback Django-Admin*-Hinweise in den Guides beschreiben jeweils den Admin-Weg für einen Vorgang, der auch im Frontend möglich ist.

## Beispiel-Gruppen

Drei Gruppen als Ausgangspunkt; die Berechtigungen werden im Admin unter *Gruppen* zusammengestellt. Immer mit einem Nicht-Superuser-Testkonto prüfen.

| Gruppe | Berechtigungen | Ergebnis |
|---|---|---|
| Helpdesk / Ausleihe | `core.view_device`, `core.view_person`, `core.view_lentrecord`, `core.transition_can_lend_device`, `core.transition_can_relocate_device` | Sieht Geräte, Personen und Ausleihen; kann Geräte ausleihen, zurücknehmen und umziehen. |
| Inventur | `core.view_device`, `core.can_inventorize`, `core.change_inventory` | Sieht Geräte, führt die aktive Inventur durch, erreicht Inventuren und SAP-Abgleich. |
| Stammdaten / IT-Beschaffung | `core.view_device`, `core.add_device`, `core.change_device`, `core.view_room`, `core.add_room`, `core.change_room`, `core.view_devicetype`, `core.view_manufacturer`, `core.view_supplier`, `core.transition_can_order_device`, `core.transition_can_locate_device`, `core.transition_can_relocate_device` | Legt Geräte und Räume an, pflegt sie, setzt Geräte auf *Bestellt* bzw. *Lokalisiert* und zieht sie um. |

Jede dieser Gruppen wird zusätzlich dem passenden Tenant zugeordnet, damit ihre Mitglieder Geräte sehen.
