# UDB

Die DLCDB kann die Personendaten (z.B. für den Verleih) mit der UDB abgleichen.

## Ziele

- **[Autarkie]** Die DLCB bleibt voll funktionsfähig, auch wenn keine UDB-Daten abgreifbar oder vorhanden sind.
- **[Redundanz]** Die Personen- und Vertragsdaten aus der UDB für den DLCDB-Verleih nutzen.
- Die UDB soll wissen, welche Devices eine Person ausgehliehen hat (siehe[API](api))

## User stories

- **[Constraint]** Ein Gerät soll nur an Personen ausgeliehen werden, die einen aktuell laufenden Vertrag haben.
- **[Notification]** Läuft ein Vertrag bald ab und sind weiterhin noch Geräte an die entsprechende Person verliehen, dann soll diese Person benachrichtigt werden.
- **[Notification]** Ist ein Vertrag abgelaufen und es sind weiterhin Leihgaben eingetragen, wird die Person angeschrieben.
- **Helpdesk**
  - User steht am Helpdesk und hätte gerne ein Notebook.
  - MA sucht im DLCDB-Verleih ein geeignetes Gerät
  - MA sucht im DLCDB-Verleih bei der Personenzurodnung die betreffende Person
    - Fall 1: Person gefunden -> Ausleihe
    - Fall 2: Person nicht gefunden -> Ausleihe verweigert
    - Fall 3: Person nicht gefunden -> Person wird manuell in DLCDB eingetragen -> Ausleihe

## Quirks

- UDB-API ist aus aktuellem Netzwerksegment von der DLCDB nicht abfragbar.
  - **Lösung:** Erzeugung eines JSON und verschieben des JSON ins Netzwerksegment der DLCDB.
- Personen, die keinen aktuellen Vertrag mehr haben, müssen weiterhin als Datenbankobjekte in der DLCDB vorhanden sein (Audit, Historie etc.).
  - **Lösung:** Abgelaufene Verträge bzw. Personen werden soft-deleted, sofern sie keine aktuellen Ausleihen mehr haben.
- Datenänderungen in der UDB (Vertragsverlängerung etc.) muss der DLCDB bekannt setting_namesein.
  - **Lösung:** Ein cronjob (huey) updated das DLCDB-Person-Model regelmäßig.
- DLCDB hat Personen, für die keine Daten in der UDB zu finden sind.
  - **Lösung:** Ist kein Problem, sondern eine Flexibilität.

## Gespiegelte Felder

Für diese use cases müssen die folgenden Informationen aus der UDB in der DLCDB vorhanden sein/gespiegelt werden:

- Vorname
- Nachname
- Institutsemailadresse
- Persönliche Emailadresse
- Vertragsbegin
- Vertragsende
- Vertragstyp und Position (z.B. zur Einschätzung welche Geräteklassen verliehen werden)

## Scheduler

Sofern die UDB-Integration aktiviert und konfiguriert ist (siehe `env.template`) werden die Personendaten alle 10 Minuten in der DLCDB mit den Daten aus der UDB aktualisiert.
