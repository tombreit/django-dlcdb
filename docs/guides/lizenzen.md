# Lizenzen

- Lizenzverwaltung: {{ licenses_fe_link }}
- Hat eine Lizenz eine Notiz, wird ein Sprechblasenicon angezeigt. Klicken auf das Sprechblasenicon zeigt oder versteckt die Notiz.

## Screenshots

### Lizenzen Übersicht

![Licenses dashboard](/_static/licenses-dashboard.webp)

### Lizenz Detailseite

![Licenses detail page](/_static/licenses-detail.webp)

## Bedienung

(subscribers)=
### Subscribers / Abonnenten

Als "Subscriber" oder Abonnenten können beliebige Emailadressen (kommagetrennt) eingegeben werden. Diese Abonnenten werden über bestimmte Zustände der entsprechenden Lizenz - z.B. *Lizenz eingetragen*, *Lizenz läuft bald ab*, *Lizenz ist abgelaufen* - via Email benachrichtigt.

## Definitionen

Damit ein Device eine Lizenz ist/wird:

- Ein Device muss das Häkchen bei *Ist Lizenz?* haben
- Ein Device muss einen Record (z.B. *Lokalisiert im Lizenzraum*) haben
- Diese Eigenschaften werden beim Eintrag über die Lizenzverwaltung automatisch gesetzt.

Eine Lizenz kann:

- Eine Liste von Emailadressen (getrennt durch Komma) haben, die zum aktuellen Stand (Lizenz ist eingetragen, Lizenz läuft bald ab, Lizenz ist abgelaufen) automatisch benachrichtigt werden.

Eine Lizenz sollte:

- Eine Datumsangabe bei *Advanced Options > Kaufdatum* haben
- Eine Datumsangabe bei *Advanced Options > Ablaufdatum Lizenz- oder Wartungsvertrag* haben
- Einen passenden Eintrag beim *Geräte-Typ* (z.B. *Lizenz - Grafik*) haben
- Entsprechende Lizenzinformationen (Seriennummer, Ansprechpartner, Ablage Keyfile etc.) im Notizfeld haben
- Eine Lizenzverlängerung, die eine neue SAP-Nummer bekommt, wird als neues Device eingetragen (z.B. via bisheriges Lizenz-Device öffnen und *Save as new*)

Eine Lizenz gilt als ausgeben/genutzt, wenn sie:

- einer Person zugeordnet ist (hier ist nicht der "Verleih" gemeint, sondern schlicht das Feld *Person* im Lizenz-Admin)
- einem Device zugeordnet ist

Der [Lizenzadmin](https://fqdn/admin/core/licencerecord/) gibt Auskuft über:

- den Expiry-Status von Lizenzen, inkl. einer 60-tägigen Warnfrist vor Ablauf
- den *ist ausgegeben/genutzt* Status
