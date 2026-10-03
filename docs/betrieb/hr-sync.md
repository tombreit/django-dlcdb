# HR-Sync

Die DLCDB kann die Personendaten (z.B. für den Verleih) mit einem HR-System (Personal-/Vertragsverwaltung) über dessen API abgleichen.

## Ziele

- **[Autarkie]** Die DLCDB bleibt voll funktionsfähig, auch wenn keine HR-Daten abgreifbar oder vorhanden sind.
- **[Redundanz]** Die Personen- und Vertragsdaten aus dem HR-System für den DLCDB-Verleih nutzen.
- Das HR-System soll wissen, welche Devices eine Person ausgeliehen hat (siehe [API](api))

## User stories

- **[Constraint]** Ein Gerät soll nur an Personen ausgeliehen werden, die einen aktuell laufenden Vertrag haben.
- **[Notification]** Läuft ein Vertrag bald ab und sind weiterhin noch Geräte an die entsprechende Person verliehen, dann soll diese Person benachrichtigt werden.
- **[Notification]** Ist ein Vertrag abgelaufen und es sind weiterhin Leihgaben eingetragen, wird die Person angeschrieben.

## Quirks

- HR-API ist aus aktuellem Netzwerksegment von der DLCDB nicht abfragbar.
  - **Lösung:** Erzeugung eines JSON und verschieben des JSON ins Netzwerksegment der DLCDB.
- Personen, die keinen aktuellen Vertrag mehr haben, müssen weiterhin als Datenbankobjekte in der DLCDB vorhanden sein (Audit, Historie etc.).
  - **Lösung:** Abgelaufene Verträge bzw. Personen werden soft-deleted, sofern sie keine aktuellen Ausleihen mehr haben.
- Datenänderungen im HR-System (Vertragsverlängerung etc.) sollte sich die DLCDB holen und abgleichen.
  - **Lösung:** Ein cronjob (huey) updated das DLCDB-Person-Model regelmäßig.
- DLCDB hat Personen, für die keine Daten im HR-System zu finden sind.
  - **Lösung:** Ist kein Problem, sondern eine Flexibilität.

## Gespiegelte Felder

Für diese use cases müssen die folgenden Informationen aus dem HR-System in der DLCDB vorhanden sein/gespiegelt werden:

- Vorname
- Nachname
- Institutsemailadresse
- Persönliche Emailadresse
- Vertragsbegin
- Vertragsende
- Vertragstyp und Position (z.B. zur Einschätzung welche Geräteklassen verliehen werden)

## Zuordnung

Jeder HR-Vertrag wird einer DLCDB-Person zugeordnet, in dieser Reihenfolge:

1. über die HR-UUID der Person (bereits verknüpfte Personen);
2. über die Institutsemailadresse oder die persönliche Emailadresse, aber nur bei Personen ohne HR-Verknüpfung;
3. über Vor- und Nachname (Groß-/Kleinschreibung egal), ebenfalls nur bei Personen ohne HR-Verknüpfung.

Hat die DLCDB-Person noch keine Emailadresse, übernimmt der Sync die Institutsemailadresse aus dem HR-System. Gehört diese Adresse bereits einer anderen DLCDB-Person ohne HR-Verknüpfung, ist das dieselbe Person, nur doppelt angelegt (etwa einmal als Ausleiher, einmal durch den Sync). Der Sync führt beide zusammen: Ausleihen, Gerätekontakte, Benachrichtigungen, Kleinkram und Lizenz-Standardabonnenten des Duplikats gehen an die verknüpfte Person, das Duplikat wird gelöscht. Die Zusammenführung steht in der Admin-Historie der Person und im Protokoll des Sync-Laufs.

Ist die andere Person selbst mit einem anderen HR-Datensatz verknüpft, führt das HR-System zwei Personen mit derselben Adresse. Dann führt der Sync nichts zusammen, sondern meldet den Konflikt mit beiden Personen und ihren HR-Verknüpfungen; die Adresse ist im HR-System zu korrigieren.

## Konfiguration

Die HR-Integration wird im Django-Admin konfiguriert: *Data exchange › HR API Sync Configuration* (Singleton).

- **enabled** – aktiviert Cronjob und Management-Command.
- **url** – die vollständige URL ohne Query-String: entweder der HR-API-Endpunkt (z.B. `https://hr.example.org/api/external_interface/contracts/`) oder eine fertige JSON-Datei. Filter und Felder hängt der Code an (eine statische JSON-Datei ignoriert sie).
- **api_token** – wird als `X-API-KEY`-Header gesendet (im Klartext gespeichert).

Request-Filter (nur aktive Verträge, keine Testdaten) und abgefragte Felder sind bewusst im Code verankert (`dlcdb/dataexchange/udb_sync.py`), nicht konfigurierbar.

## Scheduler

Ist die Integration aktiviert, werden die Personendaten alle 10 Minuten abgeglichen (huey-Task `task_import_udb_persons`). Manueller Anstoß per `./manage.py udb_sync_persons` oder im Admin über die Aktion „Run HR API sync now“.
