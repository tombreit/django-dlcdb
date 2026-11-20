# Berechtigungen

Wer in der DLCDB was sehen und tun darf, ergibt sich aus drei Dingen:

1. der **Stufe** des Benutzerkontos (Benutzer, *Staff*, *Superuser*),
2. den **Berechtigungen** der Gruppen, in denen das Konto Mitglied ist,
3. den **Mandanten**, die sich aus diesen Gruppen ergeben.

Die Einrichtung Schritt für Schritt beschreibt [Erste Schritte](erste_schritte.md). Was eine Berechtigung freischaltet, zeigt die DLCDB selbst: auf der Seite jeder Gruppe.

## Benutzer und Personen

*Benutzer* melden sich an der DLCDB an und arbeiten mit ihr: *Einstellungen › Benutzer*. Die DLCDB verschickt dabei keine Mail; ein Anfangspasswort gibt, wer das Konto anlegt, selbst weiter. Mit [LDAP](#ldap) entstehen Konten auch beim ersten Login.

*Personen* sind „Kunden“ der DLCDB, z.B. Menschen, denen ein Gerät ausgeliehen wird. Sie werden unter *Datenhaltung › Personen* gepflegt und haben nichts mit Benutzerkonten oder Berechtigungen zu tun.

## Drei Stufen: Benutzer, Staff, Superuser

| Stufe | Flag am Benutzer | Bedeutung |
|---|---|---|
| Benutzer | – | Arbeitet im Frontend und darf genau das, was die Berechtigungen seiner Gruppen erlauben. |
| Staff | *Mitarbeiter-Status* (`is_staff`) | Zusätzlich Zugang zum [Django-Admin](#django-admin); nur dann erscheinen auch die Menüpunkte, die dorthin führen. Auch dort gelten die Gruppen-Berechtigungen. |
| Superuser | *Administrator-Status* (`is_superuser`) | Hat implizit **alle** Berechtigungen, sieht also jeden Menüpunkt und jeden Statuswechsel. Geräte sieht auch ein Superuser nur in seinen [Mandanten](#mandanten). |

`./manage.py createsuperuser` setzt beide Flags, ein Superuser ist also immer auch Staff. Für die tägliche Arbeit ist keines der beiden Flags nötig; gesetzt werden sie im Django-Admin oder über LDAP.

:::{warning}
**Berechtigungen nie als Superuser testen.** Ob eine Gruppe das Richtige freischaltet, zeigt nur ein Testkonto **ohne** Superuser-Flag.
:::

## Gruppen und Berechtigungen

Berechtigungen werden **Gruppen** zugewiesen, nicht einzelnen Benutzern: *Einstellungen › Gruppen und Berechtigungen*. Die Seite einer Gruppe listet die Berechtigungen, die die DLCDB prüft, geordnet wie ihre Menüs und jede mit dem Menüpunkt, den sie freischaltet; dort werden auch die Mitglieder und die Mandanten der Gruppe gesetzt. Gruppenprofile, die die DLCDB mitbringt, sind ein Ausgangspunkt: Sie kreuzen ihre Berechtigungen an, auf *Neue Gruppe* wie auf der Seite einer Gruppe.

### LDAP

Ist die Anmeldung via LDAP eingeschaltet (`AUTH_LDAP` in der `.env`, siehe [Setup](../betrieb/setup.md)), steuern LDAP-Gruppen Anmeldung, Flags und Gruppen:

- **Anmelden** darf, wer Mitglied von `AUTH_LDAP_REQUIRE_GROUP`, `AUTH_LDAP_GROUP_STAFF` oder `AUTH_LDAP_GROUP_SUPERUSERS` ist.
- **Flags:** Mitglieder von `AUTH_LDAP_GROUP_STAFF` erhalten das Staff-Flag, Mitglieder von `AUTH_LDAP_GROUP_SUPERUSERS` Staff- und Superuser-Flag. Alle Flags, auch *Aktiv*, werden bei jedem Login neu aus LDAP gesetzt: Ein deaktivierter Benutzer ist nach dem nächsten Login wieder aktiv, solange er in der LDAP-Gruppe ist.
- **Gruppen:** Die in `AUTH_LDAP_MIRROR_GROUPS` genannten LDAP-Gruppen werden als DLCDB-Gruppen gespiegelt; ihre Mitglieder setzt LDAP bei jedem Login. Eine gespiegelte Gruppe entsteht beim ersten Login eines Mitglieds; soll sie vorher Berechtigungen und Mandanten bekommen, unter *Neue Gruppe* eine Gruppe mit exakt dem LDAP-Namen anlegen.

## Statuswechsel

Jeder Übergang im [Gerätelebenszyklus](../konzept.md) hat eine eigene Berechtigung; die Seite einer Gruppe listet sie unter *Gerät*. Das Menü *Neuer Zustand* auf der [Geräte-Detailseite](devices.md) bietet einen Übergang an, wenn er vom aktuellen Status aus zulässig ist **und** der Benutzer die Berechtigung hat. *Wiederherstellen* und *Wiedereingliedern* hat nach der Installation keine Gruppe: *Entfernt* ist damit ein Endzustand, bis jemand sie bewusst vergibt.

Eine Berechtigung schaltet nicht nur den Eintrag auf der Geräteseite frei, sondern auch die dahinterliegende Ansicht und deren Geräteauswahl. Wer z.B. nur *Gefunden* hat, findet im Menüpunkt *Umziehen* ausschließlich die als *nicht auffindbar* markierten Geräte – und kann genau diese wieder einem Raum zuordnen.

## Mandanten

Ein *Mandant* (im Code *Tenant*) ist eine organisatorische Einheit, die nur ihre eigenen Geräte verwaltet. Der Mandant hängt am **Gerät**; Records, Ausleihen und Lizenzen erben ihn über ihr Gerät, Dateien (QR-Codes, Anhänge, Import-Dateien) über ihr Objekt.

Welche Mandanten ein Benutzer sieht, ergibt sich aus seinen **Gruppen**: Ein Mandant gibt den Mitgliedern der ihm zugeordneten Gruppen Zugriff auf seine Geräte (*Einstellungen › Mandanten* oder die Seite der Gruppe).

- Ein Mandant → der Benutzer sieht nur dessen Geräte.
- Mehrere Mandanten → er sieht die Geräte **aller** dieser Mandanten.
- Kein Mandant → er sieht **keine Geräte** und kann keine anlegen; ein Hinweis auf jeder Seite sagt es. Das gilt auch für Superuser.

Mandanten vergeben **keine** Berechtigungen: Was ein Benutzer tun darf, bestimmen allein seine Gruppen, der Mandant nur, welche Geräte er dabei sieht. Eine Gruppe, die alle Mandanten sehen soll (z.B. Administratoren, IT, Revision), wird **jedem** Mandanten zugeordnet, auch jedem neu angelegten. Was Mandanten nicht einschränken, nennt die Mandanten-Übersicht.

### Geräte und Importe ohne Mandant

Ältere Geräte und Importe ohne Mandant erscheinen in keiner Liste, auch nicht für Superuser. Solange es sie gibt, zeigt die DLCDB allen, die sie zuordnen dürfen, auf jeder Seite den Hinweis *N Geräte ohne Mandant!* bzw. *N Importe ohne Mandant!*. Zum Zuordnen:

1. Dem Link *Mandant zuordnen?* folgen (Django-Admin, *Start › Mandanten › Tenants*).
2. Den Ziel-Mandanten auswählen und die Aktion *Geräte und Importe ohne Mandant zuordnen* ausführen.
3. Die folgende Seite listet alle Geräte und Importe ohne Mandant. Was zu einem anderen Mandanten gehört, abwählen und bestätigen; für das Übrige die Schritte mit dessen Mandant wiederholen.

Die Aktion braucht das Staff-Flag und das Recht, Mandanten sowie Geräte bzw. Importe zu ändern; die Seite zeigt alles, was der Benutzer ändern darf, unabhängig von den eigenen Mandanten. Den Mandanten eines Imports nicht im Import-Formular des Django-Admins ändern: Speichern dort führt den Import erneut aus.

Reichen die Angaben auf der Bestätigungsseite nicht, alle Geräte einem **Zwischen-Mandanten** *Unassigned* (der IT-Gruppe zugeordnet) zuweisen und dann auf ihren Detailseiten dem richtigen Mandanten zuordnen. Den leeren Zwischen-Mandanten danach löschen.

## Django-Admin

Die tägliche Arbeit läuft im Frontend. Der Django-Admin (*Einstellungen › Mehr › Staff-Bereich (Django-Admin)*) ist nur mit Staff-Flag erreichbar, und auch dort gelten die Gruppen-Berechtigungen. Gebraucht wird er noch für:

- die Flags *Staff* und *Superuser* und das endgültige Löschen eines Benutzers (löscht auch seine Einträge im Admin-Log),
- die Einträge der Seite *Einstellungen* mit dem Abzeichen *Staff*,
- [Geräte und Importe ohne Mandant](#geräte-und-importe-ohne-mandant) zuordnen und mehrere Geräte auf einmal einem anderen Mandanten (Aktion *Ausgewählte Geräte umziehen*),
- erzeugte Reports und den SAP-Import.

Nur Superuser dürfen, unabhängig von Berechtigungen, Stammdaten im Admin endgültig löschen und *aktivieren/deaktivieren* (Soft-Delete, siehe [Model](../betrieb/model.md#softdelete)).
