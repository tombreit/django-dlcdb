========
Lizenzen
========

*Quick and dirty Lizenzverwaltung:*  `Datenhaltung > Lizenzen <https://fqdn/admin/core/licencerecord/>`_

Damit ein Device eine Lizenz ist/wird:

* Ein Device muss das Häkchen bei *Ist Lizenz?* haben
* Ein Device muss einen Record (z.B. *Lokalisiert im Lizenzraum*) haben

Eine Lizenz sollte:

* Eine Datumsangabe bei *Advanced Options > Kaufdatum* haben
* Eine Datumsangabe bei *Advanced Options > Ablaufdatum Lizenz- oder Wartungsvertrag* haben
* Einen passenden Eintrag beim *Geräte-Typ* (z.B. *Lizenz - Grafik*) haben
* Entsprechende Lizenzinformationen (Seriennummer, Ansprechpartner, Ablage Keyfile etc.) im Notizfeld haben
* Eine Lizenzverlängerung, die eine neue SAP-Nummer bekommt, wird als neues Device eingetragen (z.B. via bisheriges Lizenz-Device öffnen und *Save as new*)

Eine Lizenz gilt als ausgeben/genutzt, wenn sie: 

* einer Person zugeordnet ist (hier ist nicht der "Verleih" gemeint, sondern schlicht das Feld *Person* im Lizenz-Admin)
* einem Device zugeordnet ist

Der `Lizenzadmin <https://fqdn/admin/core/licencerecord/>`_ gibt Auskuft über:

* den Expiry-Status von Lizenzen, inkl. einer 60-tägigen Warnfrist vor Ablauf
* den *ist ausgegeben/genutzt* Status
