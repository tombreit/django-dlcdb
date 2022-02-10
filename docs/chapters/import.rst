======
Import
======


#. CSV-Import-Datei erstellen

   * :download:`CSV-Vorlage-Datei </_static/dlcdb_csv_import_template.csv>` nutzen
   * CSV-Datei mit den zu importierenden Daten vorbereiten
   * CSV-Datei muss festgelegte Spaltenköpfe enthalten
   * CSV-Datei muss UTF-8 kodiert sein und "plain text"
   * Datumsfelder müssen im Format ``YYYY-MM-DD`` angegeben werden
   * Spalte ``DEVICETYPE`` enthält den "menschenlesbaren" Bezeichner, z.B. ``Ǹotebook``
   * Spalte ``SUPPLIER``: Schreibweise (Klein-/Großschreibung etc.) beachten. Der Supplier muss identisch wie in https://fqdn/admin/core/supplier/ notiert werden.
   * Tip: LibreOffice/OpenOffice zur Bearbeitung nutzen
   * CSV-Datei mit den gewünschten Importdaten füllen
   * Devices, die keine EDV-ID oder SAP-ID haben werden NICHT importiert


#. CSV-Datei importieren

   * https://fqdn/admin/core/importerlist/
   * Datei mit eventuellen Anmerkungen (``note``) hinzufügen
   * falls vorhanden: Validierungsfehler beheben - eine Import-Datei wird nur erfolgreich importiert, wenn keine Validierungsfehler mehr vorhanden sind
   * Importierte Geräte überprüfen: Device-Liste filtern nach `Nach Via CSV-Import angelegt? <https://fqdn/admin/core/device/?is_imported__exact=1>`_
