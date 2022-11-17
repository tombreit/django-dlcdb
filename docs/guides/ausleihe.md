# Ausleihe

:::{tip}
In der Verleihansicht werden nur Geräte aufgeführt, für die die Markierung *Ist Verleihgerät?* gesetzt ist.
:::

## Features

- Automatische Notifications (Emails) an Ausleiher bei überfälliger Rückgabe

## Gerät wird ausgeliehen

- Gerät-Ausleihe wird in DLCDB geöffnet
- Ausleihfrist wird eingetragen
  - Enddatum der Ausleihe darf aktuell nicht nach dem 31.12.2099 sein
- Zubehör wird in Notiz-Feld hinterlegt
- Ausleihzettel wird generiert und ausgedruckt
- Ausleihzettel wird unterschrieben
- Gerät wird übergeben

### Gerät wird während der Ausleihe editiert

- Raumänderungen eines verliehenen Gerätes werden in der Verleihansicht des Gerätes vorgenommen

## Gerät wird zurückgegeben

- Gerät-Ausleihe wird in DLCDB geöffnet
- Rückgabedatum wird eingetragen
- Datensatz wird gespeichert

:::{tip}
Für zurückgegebene Devices wird automatisch ein `INROOM`-Record mit dem definiteren Auto-Return-Room erstellt. Der Auto-Return-Raum wird (einmalig) in der Raumverwaltung definiert.
:::
