# Notifications

Die DLCDB kann über Bestandsveränderungen Email-Benachrichtigungen
verschicken. Alle Benachrichtigungslogik lebt in der App
`dlcdb.notifications`; die App `dlcdb.reporting` erzeugt nur die
Report-Artefakte (siehe [](reporting.md)).

## Subscriptions

Eine Person (*Subscriber*) abonniert ein Ereignis (*Event*) in einem
Intervall. Es gibt zwei Arten von Subscriptions, unterschieden über das
Event:

- **Geräte-Events**: beziehen sich auf ein konkretes Gerät, z.B.
  "Lizenz XY läuft bald ab" oder "Gerät wurde umgezogen". Die
  Lizenz-Subscriptions werden derzeit automatisch über das Lizenz-Modul
  verwaltet (`dlcdb.notifications.services`).
- **Report-Events**: ein periodischer Bericht über Records eines Typs
  (z.B. lokalisiert, verliehen), optional eingeschränkt über eine
  *Condition* (z.B. "hat SAP-Nummer", "Rückgabe überfällig"). Die Mail
  enthält eine Übersicht und ein xlsx-Spreadsheet als Anhang.

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
Berichtsfenster zu verschieben.
