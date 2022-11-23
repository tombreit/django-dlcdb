# Inventur

### Verleihgeräte

- Bei verliehenen Geräten darf der Inventurstatus "Ist nicht da" nur dann gesetzt werden, wenn sichergestellt ist, dass das Gerät nicht im zugeordneten Raum und nicht bei der/dem Ausleiher\*in ist.
- Verliehen Geräte können auch einem tatsächlichen Raum zugeordnet werden. Wenn das Gerät dort nicht gefunden wird und auf "Ist nicht da ist" geklickt wird, wird das verliehen Gerät automatisch in den Raum "Extern" verschoben, der Verleih bleibt jedoch bestehen. Erst im Raum "Extern" (Hint: Raumverwaltung > Raum: `is_external`) wird beim Klick auf "Ist nicht da" der Verleih abgebrochen und der Status "Nicht auffindbar" gesetzt.
- Die Existenz von Geräten, die aktuell verliehen sind müssen vom Leihenden bestätigt werden. Das management command `verify_lendings --help` kann das Anmailen der Leihenden übernehmen.
- Die Rückmeldung des Leihenden muss als Inventur-Notiz beim Gerät eingetragen werden, z.B. "Bestätigung Besitz durch Ausleiher\*in via Email vom YYYY-MM-DD".
- Es muss sichergestellt sein, dass für jeden Verleih auch eine Unterschrift des Leihenden geleistet wurde. Die Verleihzettel sind daher ebenfalls auf Vollständigkeit zu kontrollieren.
- Beim Abschluss der Inventur kann das Formblatt "Liste im Besitz von Mitarbeitern befindlicher Sachanlagen" über die Navigation der Inventur-App (*Misc > VG bei MAs*) generiert werden.

## Inventur Prozess

1. Voraussetzungen

   - Zugriff auf die DLCDB
   - Endgerät mit aktuellem Mozilla Firefox oder Google Chrome Browser
   - Hinweis: Inventur ist auch via Smartphone möglich

2. Vorbereitung

   - "Leere" DLCDB-Instanz für die Verwaltung (im folgenden: DLCDB-Verwaltung)
   - SAP-Abzug wird via management command `mark_not_handled_assets_in_csv` von EDV-Devices bereinigt
   - Bereinigter SAP-Abzug wird in DLCDB-Verwaltung via `import_management_csv` importiert
   - Inventur und Berechtigungen werden in DLCDB-Verwaltung angelegt

3. Inventur

   - Inventur-Ansicht aufrufen: <https://fqdn/inventory/>
   - Raum auswählen
   - Geräteliste abarbeiten
   - Via Button `State` können die drei Status eines Devices angegeben werden

     - "?": Status unklar/aktuell nicht bearbeitet/hat keinen aktuellen Inventurstempel
     - "✓": Device gefunden/ist in diesem Raum
     - "❌": Device ist nicht in diesem Raum

   - Gerät in Raum gefunden, welches nicht in der Liste ist: via "Add device" hinzufügen und Status setzen
   - Es können Inventurnotizen zu jedem Gerät und/oder zu jedem Raum angegeben werden
   - Rauminventur speichern

4. Nacharbeiten

   - SAP-Ableich

## SAP-Abgleich

### Eingabe-/Ausgabedateien

- Importdateien

  Importdateien, welche aus dem SAP-System erzeugt wurden, werden vor dem Import folgendermaßen aufbereitet:

  - überflüssige Zeilen am Dateibeginn werden entfernt, die Datei muss mit den Spaltenköpfen beginnen
  - die Spaltenköpfe dürfen keine "Dubletten" enthalten. Beispielsweise kann der Spaltenkopf "Anlagenbezeichnung" mehrfach vorkommen. Ein zweites Vorkommen ist dann umzubenennen in "Anlagenbezeichnung2"
  - die Datei muss UTF-8 kodiert sein
  - Hint: SAP-Abzug mit LibreOffice Calc öffnen und als CSV-Datei abspeichern

- Ausgabedateien

  Als Ausgabedatei eines "Ableichs" produziert die DLCDB ein CSV-Format, welches direkt mit Excel geöffnet werden kann. Die Ausgabedatei ist das Ergebnis der Inventur und enthält unverändert die Spalten der Importdatei, erweitert neue Spalten mit Inventur-relevanten Daten.


### User story

- Im Backend wird eine Inventur angelegt und auf *aktiv* gesetzt
- Ich mache die Inventur mit der DLCDB
- Ein Abzug der SAP-Anlagenbuchhaltung wird in die DLCDB importiert
- Ich klicke auf Abgleich erstellen
  : - Die Inventurliste der Verwaltung wird Zeile für Zeile durchgegangen
    - Für jede Zeile wird ein Query auf die SAP-Nummer in der DLCDB gemacht
    - Wird das Objekt in der DLCDB nicht gefunden, wird in die neue SPALTE STATUS ein "NICHT IN DLCDB" angehängt
    - Wird ein Objekt gefunden, wird dies ebenfalls mit weiteren Metadaten (wann, von wem, Notiz) angehängt.


## QR-Code-basierte Inventur (currently disabled)

(section-qr-user-story)=

### User story

Eine Inventur steht an. Person läuft mit mobilem Endgerät mit Kamera (Smartphone, Tablet) durch die Räume und scannt die Etiketten mit QR-Codes ein. Werden in einem Raum QR-Codes von Devices gescannt, die bisher nicht diesem Raum zugeordnet wurden, werden sie dem Raum zugeordnet.

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
