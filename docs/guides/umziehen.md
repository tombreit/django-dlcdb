# Umziehen

## Umzug eines einzelnen Gerätes

- Umzuziehendes Gerät in der Geräte-Übersicht (*Hauptmenü › Geräte*) aufrufen. Such-, Filter- und Sortierfunktionen können bei der Auswahl hilfreich sein.
- Im Dropdown-Menü "Lokalisiert" auswählen.
- Neuen Raum angeben.
- Neue Raumzuordnung speichern.

:::{warning}
Ist ein Device aktuell "verliehen" und wird wie oben beschrieben "lokalisiert", wird der aktuelle Verleih damit beendet und ein "InRoomRecord" für dieses Gerät erstellt. Ist eine Raumänderung eines verliehenen Geräts gewünscht, so ist diese in der Verleihansicht des Devices vorzunehmen.
:::


## Umzug mehrerer Geräte

- Menüpunkt *Umziehen* im Hauptmenü aufrufen.
- Umzuziehende Geräte auswählen (Mehrfachauswahl; die Suche hilft bei der Auswahl).
- Neuen Raum angeben.
  - Nur für Superuser: Es kann auch ein neuer Tenant angegeben werden.
- Umzug speichern.

![Umziehen mehrerer Geräte](/_static/relocate.webp){.sd-card}

:::{note}
**Fallback Django-Admin:** Der Massen-Umzug ist alternativ auch im
Device-Admin über die Action *Relocate* möglich.
:::
