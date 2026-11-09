# HR-Sync

Die DLCDB kann Personen samt Vertragsdaten aus einem HR-System (Personal-/Vertragsverwaltung) übernehmen. Sie funktioniert auch ohne: Personen lassen sich jederzeit von Hand anlegen, und Personen ohne HR-Datensatz bleiben unberührt.

## Was übernommen wird

Aus jedem aktiven Vertrag (ohne Testdaten):

- Vor- und Nachname, Institutsemailadresse, persönliche Emailadresse, Foto
- Vertragsbeginn und -ende, Vertragstyp, Organisationseinheit, Position(en)
- der Raum der Person und der Link auf seinen Raumplan (siehe [Raum](#raum))

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

- **room_number_pattern**, **room_number_replacement** – die Regel, die aus dem Raum des HR-Systems eine DLCDB-Raumnummer macht (siehe [Raum](#raum)).

Request-Filter (nur aktive Verträge, keine Testdaten) und abgefragte Felder sind bewusst im Code verankert (`dlcdb/dataexchange/udb_sync.py`), nicht konfigurierbar.

## Raum

Das HR-System nennt den Raum einer Person in den Ressourcen des Vertrags, als Ressource vom Typ `arbeitsplatz`. Am CSL ist das ein Arbeitsplatz in einem Raum: `Gü-235-02` ist Arbeitsplatz 02 in Raum G235.

Eine Regel macht daraus die DLCDB-Raumnummer: ein regulärer Ausdruck (Python-Syntax) und eine Ersetzung, angewandt wie bei [Räume umbenennen](../guides/erste_schritte.md#räume-umbenennen). Am CSL: Muster `^(\w)\w*-(\d+)-\d+$`, Ersetzung `\1\2`. Ohne Muster gilt der Wert aus dem HR-System unverändert als Raumnummer.

- Der Sync setzt den Raum jeder Person, die er abgleicht; Groß-/Kleinschreibung der Raumnummer ist egal. Nennt das HR-System keinen Raum, verliert die Person ihren Raum. Personen ohne HR-Verknüpfung behalten den Raum, der ihnen von Hand zugewiesen ist.
- Der Sync legt keine Räume an. Gibt es den Raum in der DLCDB nicht (oder ist er deaktiviert), bekommt die Person keinen Raum, und das Protokoll des Sync-Laufs meldet ihn, etwa `HR room Gü-999-01 → G999: no such room in DLCDB`. Dann den Raum anlegen oder [umbenennen](../guides/erste_schritte.md#räume-umbenennen).
- Den ersten Link der Ressource (am CSL der Mapongo-Raumplan) übernimmt der Sync als *Website* des Raums und überschreibt dabei eine von Hand eingetragene. Die Änderung steht in der Admin-Historie des Raums und im Protokoll des Sync-Laufs.

Reihenfolge beim Einrichten: zuerst die Räume so benennen, wie die Regel sie erzeugt, dann die Regel eintragen, dann die nächsten Sync-Läufe auf gemeldete Räume prüfen.

## Scheduler

Ist die Integration aktiviert, werden die Personendaten alle 10 Minuten abgeglichen. Manueller Anstoß per `./manage.py udb_sync_persons` oder im Admin über die Aktion „Run HR API sync now“.
