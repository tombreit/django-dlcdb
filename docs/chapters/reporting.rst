=========
Reporting
=========

Prosa
-----

Die DLCDB kann über bestimmte Bestandsveränderungen Email-Benachrichtigungen verschicken.

Es existieren zwei Modi:

* "Abo-Modell interne Adressaten": User können sich für bestimmte Zeitintervalle zu bestimmten Ereignissen bei bestimmten Bedingungen Emails schicken lassen.

  *Beispiel:* 

  Die Verwaltung (*Empfänger* oder *Abonnent*) will jeden Monat (*Zeitintervall*) über deinventarisierte (*Ereignis*) Devices mit einer SAP-Nummer (*Bedingung*) informiert werden.

* "Benachrichtigung externer Adressaten": Personen (``class Person``) können automatisiert und zeitgesteuert (cron-like) via Email benachrichtigt werden; z.B. über überfällige Ausleihen.


Implementation
--------------

Ablauf periodischer Aufruf via huey
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   graph TD
      A(Zeitintervall erreicht) -->|get notifications for interval|B
      B[Notification] --> |get_affected_records for now minus interval|C
      C[Report] --> D
      D(Email) --> E
      E[Notification] --> |set last_run, save|F
      F[Done]


Ablauf manueller Aufruf via Notification-save
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. mermaid::

   graph TD
      B[Notification] --> |save, get_affected_records for now minus last_run|C
      C[Report] --> D
      D(Email) --> E
      F[Done]
