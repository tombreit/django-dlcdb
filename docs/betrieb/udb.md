# UDB

Die DLCDB kann die Personendaten (z.B. für den Verleih) mit der UDB abgleichen.

## Ziele

- **[Autarkie]** Die DLCDB bleibt voll funktionsfähig, auch wenn keine UDB-Daten abgreifbar oder vorhanden sind.
- **[Redundanz]** Die Personen- und Vertragsdaten aus der UDB für den DLCDB-Verleih nutzen.
- Die UDB soll wissen, welche Devices eine Person ausgeliehen hat (siehe [API](api))

## User stories

- **[Constraint]** Ein Gerät soll nur an Personen ausgeliehen werden, die einen aktuell laufenden Vertrag haben.
- **[Notification]** Läuft ein Vertrag bald ab und sind weiterhin noch Geräte an die entsprechende Person verliehen, dann soll diese Person benachrichtigt werden.
- **[Notification]** Ist ein Vertrag abgelaufen und es sind weiterhin Leihgaben eingetragen, wird die Person angeschrieben.

## Quirks

- UDB-API ist aus aktuellem Netzwerksegment von der DLCDB nicht abfragbar.
  - **Lösung:** Erzeugung eines JSON und verschieben des JSON ins Netzwerksegment der DLCDB.
- Personen, die keinen aktuellen Vertrag mehr haben, müssen weiterhin als Datenbankobjekte in der DLCDB vorhanden sein (Audit, Historie etc.).
  - **Lösung:** Abgelaufene Verträge bzw. Personen werden soft-deleted, sofern sie keine aktuellen Ausleihen mehr haben.
- Datenänderungen in der UDB (Vertragsverlängerung etc.) sollte sich die DLCDB holen und abgleichen.
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

## Konfiguration

Die UDB-Integration wird im Django-Admin konfiguriert: *Data exchange › UDB Sync Configuration* (Singleton).

- **enabled** – aktiviert Cronjob und Management-Command.
- **url** – die vollständige URL ohne Query-String: entweder der UDB-API-Endpunkt (z.B. `https://udb.example.org/api/external_interface/contracts/`) oder eine fertige JSON-Datei. Filter und Felder hängt der Code an (eine statische JSON-Datei ignoriert sie).
- **api_token** – wird als `X-API-KEY`-Header gesendet (im Klartext gespeichert).

Request-Filter (nur aktive Verträge, keine Testdaten) und abgefragte Felder sind bewusst im Code verankert (`dlcdb/dataexchange/udb_sync.py`), nicht konfigurierbar.

## Scheduler

Ist die Integration aktiviert, werden die Personendaten alle 10 Minuten abgeglichen (huey-Task `task_import_udb_persons`). Manueller Anstoß per `./manage.py udb_sync_persons` oder im Admin über die Aktion „Run UDB sync now“.
