# Reporting

## User stories

User Mary:

- Mary (*Subscriber*) möchte informiert (*Subscription*) werden, wenn ein Gerät seinen Standort ändert (*Event*) durch eine Nachricht (*Message*).
- Mary möchte jeden ersten des Monats über alle Standortveränderungen informiert werden. Sie bekommt einen *Report*
- Mary möchte informiert werden, wenn ein Gerät ausgemustert wird.
- Mary möchte informiert werden, wenn eine Lizenz bald abläuft.
  - Mary möchte aber nur einmal über dieses Ereignis informiert werden.
- Mary kann Benachrichtigungen für solche Ereignisse abonnieren.
- Mary could have multiple *Subscriptions*
- Mary kann ihre *Subscriptions* einsehen und verwalten.

System:

- Manages NotificationEvents in a queue.
- Regulary processes this queue and send pending Notifications and stores a return value

## Prosa

Die DLCDB kann über bestimmte Bestandsveränderungen Email-Benachrichtigungen verschicken.

- "Intervall-basiert/Abo-Modell": User können sich für bestimmte Zeitintervalle zu bestimmten Ereignissen bei bestimmten Bedingungen Emails schicken lassen.

  *Beispiel:*

  Die Verwaltung (*Subscriber*) will jeden Monat (*Zeitintervall*) über deinventarisierte (*Event*) Devices mit einer SAP-Nummer (*Condition*) informiert werden.

- "Trigger-basiert": Personen (`class Person`) können automatisiert via Email benachrichtigt bei Eintreten von bestimmten Bedingungen benachrichtigt werden; z.B. über überfällige Ausleihen.

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
