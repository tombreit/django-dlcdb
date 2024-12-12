# Reporting

## User stories

User Mary:

- Mary (*Subscriber*) möchte informiert (*Notification*) werden, wenn ein Gerät seinen Standort ändert (*NotificationEvent*)
- Mary möchte jeden ersten des Monats über alle Standortveränderungen informiert werden. Sie bekommt einen *Report*
- Mary möchte informiert werden, wenn ein Gerät ausgemustert wird.
- Mary möchte informiert werden, wenn eine Lizenz bald abläuft
  - Mary möchte aber nur einmal über dieses Ereignis informiert werden.
- Mary kann Benachrichtigungen für solche Ereignisse abonnieren.
- Mary could have multiple *Subscriptions*

System:

- Manages NotificationEvents in a queue.
- Regulary processes this queue and send pending Notifications and stores a return value

## Prosa

Die DLCDB kann über bestimmte Bestandsveränderungen Email-Benachrichtigungen verschicken.

Es existieren zwei Modi:

- "Abo-Modell interne Adressaten": User können sich für bestimmte Zeitintervalle zu bestimmten Ereignissen bei bestimmten Bedingungen Emails schicken lassen.

  *Beispiel:*

  Die Verwaltung (*Empfänger* oder *Abonnent*) will jeden Monat (*Zeitintervall*) über deinventarisierte (*Ereignis*) Devices mit einer SAP-Nummer (*Bedingung*) informiert werden.

- "Benachrichtigung externer Adressaten": Personen (`class Person`) können automatisiert und zeitgesteuert (cron-like) via Email benachrichtigt werden; z.B. über überfällige Ausleihen.

## Implementation

### Ablauf periodischer Aufruf via huey

```{eval-rst}
.. mermaid::

   graph TD
      A(Zeitintervall erreicht) -->|get notifications for interval|B
      B[Notification] --> |get_affected_records for now minus interval|C
      C[Report] --> D
      D(Email) --> E
      E[Notification] --> |set last_run, save|F
      F[Done]

```

### Ablauf manueller Aufruf via Notification-save

```{eval-rst}
.. mermaid::

   graph TD
      B[Notification] --> |save, get_affected_records for now minus last_run|C
      C[Report] --> D
      D(Email) --> E
      F[Done]
```
