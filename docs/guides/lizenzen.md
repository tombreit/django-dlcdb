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

Abonnenten sind [Personen](erste_schritte.md#7-personen-anlegen) mit Email-Adresse. Sie werden über Zustände der Lizenz – z.B. *Lizenz eingetragen*, *Lizenz läuft bald ab*, *Lizenz ist abgelaufen* – per Email benachrichtigt (siehe [Notifications](notifications.md)). Standard-Abonnenten für alle neuen Lizenzen stehen in der *Lizenzmodul Konfiguration*.

## Definitionen

Damit ein Device eine Lizenz ist/wird:

- Ein Device muss das Häkchen bei *Ist Lizenz?* haben
- Ein Device muss einen Record (z.B. *Lokalisiert im Lizenzraum*) haben
- Diese Eigenschaften werden beim Eintrag über die Lizenzverwaltung automatisch gesetzt.

Wie Geräte gehören Lizenzen zu einem [Mandanten](berechtigungen.md#mandanten).

Eine Lizenz sollte:

- Eine Datumsangabe bei *Beschaffung › Kaufdatum* haben
- Eine Datumsangabe bei *Beschaffung › Ablaufdatum Lizenz- oder Wartungsvertrag* haben
- Einen passenden Eintrag beim *Geräte-Typ* (z.B. *Lizenz - Grafik*) haben
- Entsprechende Lizenzinformationen (Seriennummer, Ansprechpartner, Ablage Keyfile etc.) im Notizfeld haben
- Eine Lizenzverlängerung, die eine neue SAP-Nummer bekommt, wird als neues Device eingetragen (z.B. bisheriges Lizenz-Device öffnen und *Als neu speichern*)

Eine Lizenz gilt als ausgeben/genutzt, wenn sie:

- einer Person zugeordnet ist (hier ist nicht der "Verleih" gemeint, sondern schlicht das Feld *Person* im Lizenz-Formular)
- einem Device zugeordnet ist

Die Lizenzverwaltung ({{ licenses_fe_link }}) gibt Auskunft über:

- den Expiry-Status von Lizenzen, inkl. einer 60-tägigen Warnfrist vor Ablauf
- den *ist ausgegeben/genutzt* Status

## Kalender-Abo (ICS)

Auf der Detailseite einer Lizenz steht ein ICS-Kalender-Link zur
Verfügung. Damit lassen sich Ablaufdaten einer Lizenz direkt in den
eigenen Kalender (Outlook, Thunderbird, etc.) übernehmen.
