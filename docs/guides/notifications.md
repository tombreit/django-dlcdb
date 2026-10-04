# Notifications

Die DLCDB verschickt drei Arten von Email-Benachrichtigungen:

| Art | Empfänger | Auslöser |
|---|---|---|
| [Berichte](#berichte-abonnieren) über Records eines Typs | wer sie abonniert hat | Intervall des Abonnements |
| [Lizenz-Ereignisse](#lizenz-ereignisse) | die Abonnenten der Lizenz | Lizenz eingetragen, läuft bald ab, abgelaufen |
| [Erinnerungen an überfällige Ausleihen](#erinnerungen-an-überfällige-ausleihen) | Ausleihende und/oder IT | wöchentlich |

Jede Mail, ob versendet oder fehlgeschlagen, steht im Journal (*Einstellungen › Journal*).

## Berichte abonnieren

Über *Abonnements* im Benutzermenü verwaltet jeder Benutzer seine eigenen Bericht-Abonnements:

- **Abonnieren:** ein Ereignis (z.B. *Report: Lent devices*), optional eine *Bedingung* (z.B. *Überfällige Rückgabe*, *Hat SAP-Nummer*), ein *Intervall* und ob auch dann gemailt wird, wenn keine Records passen. Die Mail enthält eine Übersicht und die Records als xlsx-Anhang.
- **Verwalten:** *Deaktivieren*/*Aktivieren*, *Löschen* oder sofort eine *Ad-hoc Meldung* versenden, ohne den regulären Termin zu verschieben. Ändern lässt sich ein Abonnement nicht; dafür löschen und neu anlegen.

Abonnieren kann nur, wessen Email-Adresse zu einer [Person](erste_schritte.md#7-personen-anlegen) gehört; sonst zeigt die Seite nur einen Hinweis.

## Lizenz-Ereignisse

Die {ref}`Abonnenten einer Lizenz <subscribers>` erhalten automatisch eine Mail, wenn die Lizenz eingetragen wird, 30 Tage vor ihrem Ablauf und am Ablaufdatum. Diese Abonnements entstehen und verschwinden mit der Lizenz. Auf der Seite *Abonnements* erscheinen sie nur zur Ansicht, mit einem Link zur Lizenz.

## Erinnerungen an überfällige Ausleihen

Jeden Montag erhält jede Person mit überfälligen Ausleihen eine Mail, die ihre überfälligen Geräte auflistet (eine Mail je Mandant). Wer sie bekommt, legt *Einstellungen › Ausleihe Konfiguration* fest:

- *Nobody*: keine Mails
- *Lender*: an die ausleihende Person
- *Lender, IT in CC*: an die Person, die IT in Kopie
- *IT only*: nur an die IT (zum Testen: dieselbe Mail, umgeleitet)

Die IT-Adresse ist die Kontakt-Email des [Mandanten](berechtigungen.md#mandanten) der Geräte, ersatzweise die IT-Adresse aus dem Branding, zuletzt `DEFAULT_FROM_EMAIL`. Unabhängig davon zeigt das Dashboard die Zahl der überfälligen Ausleihen.

## Betrieb

Ein Task des Task Runners prüft jede Minute, welche Abonnements fällig sind, und versendet deren Mails; ohne laufenden Task Runner geht keine Mail hinaus (siehe [Setup](../betrieb/setup.md)). Im Django-Admin lassen sich alle Nachrichten (Status, Vorschau, *Send Now*) und die erzeugten Berichte einsehen. Welche Felder ein Bericht enthält, legt `EXPOSED_FIELDS` in `dlcdb/reporting/settings.py` fest.
