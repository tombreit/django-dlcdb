# Import

Devices können per CSV-Datei in die DLCDB importiert werden. Der Import
erfolgt über die Geräte-Übersicht (*Hauptmenü › Geräte*, Button
*Import*) und läuft in zwei Schritten: Nach dem Hochladen wird die Datei
zunächst nur validiert und eine Vorschau angezeigt — erst nach
Bestätigung wird tatsächlich importiert.

1. CSV-Import-Datei erstellen

   - CSV-Vorlage nutzen: Download-Link auf der Import-Seite (alternativ:
     {download}`CSV-Vorlage-Datei </_static/dlcdb_csv_import_template.csv>`)
   - CSV-Datei mit den zu importierenden Daten vorbereiten
   - CSV-Datei muss festgelegte Spaltenköpfe enthalten
   - CSV-Datei muss UTF-8 kodiert sein und "plain text"
   - Datumsfelder müssen im Format `YYYY-MM-DD` angegeben werden
   - Spalte `DEVICETYPE` enthält den "menschenlesbaren" Bezeichner, z.B. `Notebook`
   - Spalte `SUPPLIER`: Schreibweise (Klein-/Großschreibung etc.) beachten. Der Zulieferer muss identisch wie unter *Datenhaltung › Zulieferer* notiert werden.
   - Tip: LibreOffice/OpenOffice zur Bearbeitung nutzen
   - Devices, die keine EDV-ID oder SAP-ID haben, werden NICHT importiert

2. CSV-Datei hochladen und prüfen

   - *Hauptmenü › Geräte › Import*
   - Datei mit eventuellen Anmerkungen (`note`) hochladen
   - Die Vorschau zeigt Validierungsfehler an — dabei wird noch nichts
     in die Datenbank geschrieben
   - Falls vorhanden: Validierungsfehler in der CSV-Datei beheben und
     erneut hochladen. Eine Import-Datei wird nur erfolgreich
     importiert, wenn keine Validierungsfehler mehr vorhanden sind

![Import: Datei hochladen](/_static/import-upload.webp){.sd-card}

3. Import bestätigen

   - Nach fehlerfreier Validierung den Import über den
     Bestätigen-Button ausführen
   - Importierte Geräte überprüfen: Die importierten Devices sind in der
     Geräte-Übersicht als importiert markiert

![Import: Vorschau und Bestätigung](/_static/import-preview.webp){.sd-card}

:::{note}
**Import-Historie und SAP-Format.** Vergangene Importe (Audit-Trail)
sind unter *Prozesse › Bulk Import* (Django-Admin, ImporterList)
einsehbar. Dort steht auch ein experimenteller Import für
SAP-CSV-Exporte zur Verfügung — offiziell unterstützt ist nur das
DLCDB-interne CSV-Format der Vorlage.
:::
