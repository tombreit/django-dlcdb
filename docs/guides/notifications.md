# Notifications

Die DLCDB kann über Bestandsveränderungen Email-Benachrichtigungen
verschicken. Alle Benachrichtigungslogik lebt in der App
`dlcdb.notifications`. Die App `dlcdb.reporting` erzeugt dabei nur die
Report-Artefakte: tabellarische Übersichten über Records als xlsx-Spreadsheet
und Text-Repräsentation, gespeichert als `Report` (Titel, Body,
Spreadsheet-Datei unter `media/reporting/spreadsheets/`). Welche Felder in
Reports auftauchen, steuert `EXPOSED_FIELDS` in `dlcdb/reporting/settings.py`
(pro Record-Typ). Erzeugte Reports sind im Django-Admin einsehbar
(read-only, kein Add).

## Subscriptions

Eine Person (*Subscriber*) abonniert ein Ereignis (*Event*) in einem
Intervall. Es gibt zwei Arten von Subscriptions, unterschieden über das
Event:

- **Geräte-Events**: beziehen sich auf ein konkretes Gerät, z.B.
  "Lizenz XY läuft bald ab" oder "Gerät wurde umgezogen". Die
  Lizenz-Subscriptions werden derzeit automatisch über das Lizenz-Modul
  verwaltet (`dlcdb.notifications.services`, signalgetrieben beim
  Speichern/Löschen einer Lizenz, siehe `dlcdb/licenses/subscribers.py`) —
  Nutzer können diese nicht selbst anlegen oder abbestellen.
- **Report-Events**: ein periodischer Bericht über Records eines Typs
  (z.B. lokalisiert, verliehen), optional eingeschränkt über eine
  *Condition* (z.B. "hat SAP-Nummer", "Rückgabe überfällig"). Die Mail
  enthält eine Übersicht und ein xlsx-Spreadsheet als Anhang
  (erzeugt über `dlcdb.reporting.services.create_report()`).

Empfänger ist immer die Email-Adresse des Subscribers (`Person`). Mehrere
Empfänger = mehrere Subscriptions.

Daneben gibt es die **Overdue-Lender-Mails**: Personen mit überfälligen
Ausleihen werden wöchentlich automatisch erinnert (eine Mail pro Person mit
allen überfälligen Geräten). Der Empfänger wird über die *Lending
Configuration* im Admin gesteuert (`overdue_notifications_recipient`):

- *Nobody* — keine Mails
- *Lender* — Mail an die ausleihende Person
- *Lender, IT in CC* — eine Mail, Person im To, IT (`DEFAULT_FROM_EMAIL`) im CC
- *IT only* — Mail nur an IT (Testdrive: identischer Inhalt, umgeleitet)

Für eine mailfreie Übersicht zeigt das Dashboard eine Kachel mit der Anzahl
überfälliger Ausleihen, verlinkt auf die vorgefilterte Lending-Liste.

## Self-Service: eigene Report-Subscriptions verwalten

Eingeloggte Nutzer erreichen über den User-Dropdown ("Subscriptions",
`dlcdb/theme/templates/theme/includes/navbar.html`) die Seite
`notifications:index` (`dlcdb/notifications/views.py`,
`dlcdb/notifications/templates/notifications/index.html`). Dort können sie:

- eine neue Report-Subscription anlegen (Event, Condition, Intervall,
  `notify_no_updates`; `ReportSubscriptionForm` in
  `dlcdb/notifications/forms.py`),
- ihre bestehenden Report-Subscriptions in einer Tabelle einsehen,
- eine Subscription deaktivieren/reaktivieren (`toggle`) oder löschen,
- über "Trigger ad hoc report" sofort einen Report auslösen und versenden,
  ohne das reguläre Berichtsfenster zu verschieben — analog zur
  gleichnamigen Aktion im Admin.

Es gibt keine Edit-Ansicht; eine Änderung an Event/Condition/Intervall
erfolgt über Löschen und Neuanlegen.

Die Zuordnung Nutzer → `Person` (Subscriber) erfolgt über die Email-Adresse
(`Person.objects.filter(email=request.user.email)`), nicht über eine
Fremdschlüssel-Relation. Existiert keine passende `Person`, zeigt die Seite
nur einen Hinweis ohne Formular. Die Ansicht ist strikt auf die eigenen
Subscriptions beschränkt — Nutzer sehen und verwalten nie fremde
Subscriptions.

Geräte-Events (Lizenz-Ablauf, Umzug etc.) werden in derselben Tabelle
read-only mitangezeigt, mit einem Link zur jeweiligen Lizenz- bzw.
Geräte-Ansicht statt der Delete/Toggle/Trigger-Aktionen — sie werden weiterhin
ausschließlich automatisch verwaltet (siehe oben).

## Implementation

Jede Benachrichtigung wird als `Message` erzeugt (pending) und über die
konfigurierten Channels (`channels.py`, derzeit Email) versendet. Status
und Vorschau (inkl. "Send Now") pro Message im Admin.

Ein periodischer huey-Task (`process_notification_system`, minütlich)
verarbeitet fällige Subscriptions (`next_scheduled`):

```{eval-rst}
.. mermaid::

   graph TD
      A(huey: process_notification_system, minütlich) --> B{Subscription fällig?}
      B --> |Geräte-Event|C[Message aus Template]
      B --> |Report-Event|D[reporting.create_report: xlsx]
      D --> E[Message mit Report-Anhang]
      C --> F(Email-Versand via Channels)
      E --> F
      F --> G[Message: sent/failed]
```

Im Admin einer Report-Subscription kann über "Trigger ad hoc report"
jederzeit ein Report erzeugt und versendet werden, ohne das reguläre
Berichtsfenster zu verschieben — dieselbe Funktion steht Nutzern auch
selbst über die oben beschriebene Self-Service-Seite zur Verfügung.
