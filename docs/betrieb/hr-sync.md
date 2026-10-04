# HR-Sync

Die DLCDB kann Personen samt Vertragsdaten aus einem HR-System (Personal-/Vertragsverwaltung) übernehmen. Sie funktioniert auch ohne: Personen lassen sich jederzeit von Hand anlegen, und Personen ohne HR-Datensatz bleiben unberührt.

## Was übernommen wird

Aus jedem aktiven Vertrag (ohne Testdaten):

- Vor- und Nachname, Institutsemailadresse, persönliche Emailadresse, Foto
- Vertragsbeginn und -ende, Vertragstyp, Organisationseinheit, Position(en)

Das Vertragsende nutzt die [Ausleihe](../guides/ausleihe.md): Sie warnt, wenn ein Vertrag vor dem Rückgabedatum endet oder kein Vertragsende bekannt ist. Ist bei einer Ausleihe *Synchronisiere mit Vertragsenddatum* gesetzt, übernimmt der Sync jedes geänderte Vertragsende als Rückgabedatum.

Der Sync deaktiviert niemanden; eine deaktivierte Person, die wieder im HR-System auftaucht, wird reaktiviert. Welche Geräte eine Person ausgeliehen hat, kann das HR-System über die [API](api.md) abfragen.

## Zuordnung

Jeder HR-Vertrag wird einer DLCDB-Person zugeordnet, in dieser Reihenfolge:

1. über die HR-UUID der Person (bereits verknüpfte Personen);
2. über die Institutsemailadresse oder die persönliche Emailadresse, aber nur bei Personen ohne HR-Verknüpfung;
3. über Vor- und Nachname (Groß-/Kleinschreibung egal), ebenfalls nur bei Personen ohne HR-Verknüpfung.

Hat die DLCDB-Person noch keine Emailadresse, übernimmt der Sync die Institutsemailadresse. Gehört diese Adresse bereits einer anderen DLCDB-Person ohne HR-Verknüpfung, ist das dieselbe Person, nur doppelt angelegt (etwa einmal als Ausleiher, einmal durch den Sync). Der Sync führt beide zusammen: Ausleihen, Gerätekontakte, Benachrichtigungen, Kleinkram und Lizenz-Standardabonnenten des Duplikats gehen an die verknüpfte Person, das Duplikat wird gelöscht. Die Zusammenführung steht in der Admin-Historie der Person und im Protokoll des Sync-Laufs.

Ist die andere Person selbst mit einem anderen HR-Datensatz verknüpft, führt das HR-System zwei Personen mit derselben Adresse. Dann führt der Sync nichts zusammen, sondern meldet den Konflikt mit beiden Personen und ihren HR-Verknüpfungen; die Adresse ist im HR-System zu korrigieren.

## Konfiguration

Die HR-Integration wird im Django-Admin konfiguriert: *Einstellungen › HR-API-Sync-Konfiguration* (Singleton).

- **enabled** – aktiviert den periodischen Sync und das Management-Command.
- **url** – die vollständige URL ohne Query-String: entweder der HR-API-Endpunkt (z.B. `https://hr.example.org/api/external_interface/contracts/`) oder eine fertige JSON-Datei, etwa wenn die HR-API aus dem Netz der DLCDB nicht erreichbar ist. Filter und Felder hängt der Code an (eine statische JSON-Datei ignoriert sie).
- **api_token** – wird als `X-API-KEY`-Header gesendet (im Klartext gespeichert).

Request-Filter (nur aktive Verträge, keine Testdaten) und abgefragte Felder sind bewusst im Code verankert (`dlcdb/dataexchange/udb_sync.py`), nicht konfigurierbar.

## Scheduler

Ist die Integration aktiviert, werden die Personendaten alle 10 Minuten abgeglichen. Manueller Anstoß per `./manage.py udb_sync_persons` oder im Admin über die Aktion „Run HR API sync now“.
