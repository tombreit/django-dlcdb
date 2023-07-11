# Inventur

Inventur-Ansicht: *Prozesse > Inventur*


## Inventur Prozess

1. Voraussetzungen

   - Zugriff auf die DLCDB
   - Endgerät mit aktuellem Mozilla Firefox oder Google Chrome Browser
   - Hinweis: Inventur ist auch via Smartphone möglich
   - Aktuelle Inventur angelegt  markiert
   - Inventur (*Datenhaltung > Inventuren*, *Aktiv*) und Berechtigungen werden in DLCDB-Verwaltung angelegt

1. Inventur

   - Inventur-Ansicht aufrufen: <https://fqdn/inventory/> (*Prozesse > Inventur*)
   - Raum auswählen
   - Geräteliste abarbeiten
   
     Via Button `State` können die drei Status eines Devices durchgewechselt und aktiviert werden:

     - "?": Status unklar/aktuell nicht bearbeitet/hat keinen aktuellen Inventurstempel
     - "✔": Device gefunden/ist in diesem Raum
     - "❌": Device ist nicht in diesem Raum

   - Gerät ist aktuell verliehen: siehe [Hinweise Verleihgeräte](#verleihgerate)
   - Gerät in Raum gefunden, welches nicht in der Liste ist: via "Add device" hinzufügen und Status setzen
   - Es können Inventurnotizen zu jedem Gerät und/oder zu jedem Raum angegeben werden
   - Rauminventur speichern

1. Nacharbeiten

   - SAP-Ableich (*Prozesse > SAP-Abgleich*)


## Verleihgeräte

- Wird bei einem verliehenen Gerät auf "Ist nicht da ist" geklickt wird, wird das verliehen Gerät automatisch in den Raum "Extern" verschoben, der Verleih bleibt jedoch bestehen. Erst im Raum "Extern" (Hint: Raumverwaltung > Raum: `is_external`) wird beim Klick auf "Ist nicht da" der Verleih abgebrochen und der Status "Nicht auffindbar" gesetzt.
- Wird ein aktuell verliehenes Gerät in einem Raum gefunden und auf "Ist da" geklickt, wird die Raumzuordnung des Verleihs geändert, der Verleih bleibt jedoch weiterhin bestehen.
- Die Existenz von Geräten, die aktuell verliehen sind müssen vom Leihenden bestätigt werden. Das management command `verify_lendings --help` kann das Anmailen der Leihenden übernehmen.
- Die Rückmeldung des Leihenden muss als Inventur-Notiz beim Gerät eingetragen werden, z.B. "Bestätigung Besitz durch Ausleiher\*in via Email vom YYYY-MM-DD".
- Es muss sichergestellt sein, dass für jeden Verleih auch eine Unterschrift des Leihenden geleistet wurde. Die Verleihzettel sind daher ebenfalls auf Vollständigkeit zu kontrollieren.
- Beim Abschluss der Inventur kann das Formblatt "Liste im Besitz von Mitarbeitern befindlicher Sachanlagen" über die Navigation der Inventur-App (*Misc > VG bei MAs*) generiert werden.

## SAP-Abgleich

### Eingabe-/Ausgabedateien

- Importdateien

  Importdateien, welche aus dem SAP-System erzeugt wurden, werden vor dem Import folgendermaßen aufbereitet:

  - überflüssige Zeilen am Dateibeginn werden entfernt, die Datei muss mit den Spaltenköpfen beginnen
  - die Spaltenköpfe dürfen keine "Dubletten" enthalten. Beispielsweise kann der Spaltenkopf "Anlagenbezeichnung" mehrfach vorkommen. Ein zweites Vorkommen ist dann umzubenennen oder zu löschen
  - die Datei muss UTF-8 kodiert sein
  - Hint: SAP-Abzug mit LibreOffice Calc öffnen und als CSV-Datei abspeichern

- Ausgabedateien

  Als Ausgabedatei eines "Ableichs" produziert die DLCDB ein CSV-Format, welches direkt mit Excel geöffnet werden kann. Die Ausgabedatei ist das Ergebnis der Inventur und enthält unverändert die Spalten der Importdatei, erweitert um neue Spalten mit Inventur-relevanten Daten.

- Was geschieht beim SAP-Abgleich?
  : - Die Inventurliste der Verwaltung wird Zeile für Zeile durchgegangen
    - Für jede Zeile wird ein Query auf die SAP-Nummer in der DLCDB gemacht
    - Wird das Objekt in der DLCDB nicht gefunden, wird in die neue SPALTE STATUS ein "NICHT IN DLCDB" angehängt
    - Wird ein Objekt gefunden, wird dies ebenfalls mit weiteren Metadaten (wann, von wem, Notiz) angehängt.


## QR-Code-basierte Inventur

(section-qr-user-story)=

Die Inventur kann über einen eingebauten QR-Code-Scanner erfolgen:

- Tip: Mobiles Endgerät (Smartphone, Tablet) nutzen
- Inventur-Ansicht öffnen
- *QR-Scanner* (Schalter rechts oben) einschalten
- Seite neu laden
- Raum-Schild scannen, App welchselt in den gescannten Raum
- Assets scannen
- Nächstes Raum-Schild scannen
- Assets scannen
- Werden in einem Raum QR-Codes von Assets gescannt, die bisher nicht diesem Raum zugeordnet wurden, werden sie dem Raum zugeordnet.

### Bedingungen

- Smartphone/Scanner muss Zugriff auf die DLCDB haben
- Devices sind mit QR-Codes versehen, die einen bestimmten Inhalt codieren (siehe unten).

### QR-Codes

- Jedes Device hat automatisch eine eindeutige UUID
- Für jedes Gerät wird ein QR-Code geniert, der sich aus einem Prefix, einem (optionalen) Infix und einem Suffix zusammensetzt:

  * Prefix: String, wird in via `settings` definiert, dient der Unterscheidung von eigenen und fremden QR-Codes. Zum Beispiel: `DLCDB` oder `example.com`
  * Suffix: UUID eines Items, in der Regel eines Devices
  * Infix: Optionaler Identifier (String), der zwischen Prefix und Suffix steht und spezielle Items kennzeichnet, z.B. Räume.

:::{WARNING}
Do not change this prefix mid-project as it will break the scanner recognizing already printed qr codes!
:::
