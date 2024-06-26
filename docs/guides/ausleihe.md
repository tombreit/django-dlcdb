# Ausleihe

:::{tip}
In der Verleihansicht werden nur Geräte aufgeführt, für die die Markierung *Ist Verleihgerät?* gesetzt ist.
:::

## Features

- Druckbarer, gebrandeter Ausleihvertrag, inklusive Version für die Ausleihenden
- Editierbare Checkliste als Anhang zum Ausleihvertrag
- Automatische Notifications (Emails) an Ausleiher bei überfälliger Rückgabe

## Gerät wird ausgeliehen

:::{note}
Auch einem verliehenen Gerät kann ein Raum zugeordnet werden. Wenn beim Verleih davon auszugehen ist, dass das Device mit hoher Wahrscheinlichkeit in Raum X wiederzufinden, so ist hier auch Raum X einzutragen. Wenn mit hoher Wahrscheinlichkeit unklar ist, wo sich das Device befinden wird (z.B. Homeoffice-Ausleihen), kann der Raum “Extern” angegeben werden.
:::

- Gerät-Ausleihe wird in DLCDB geöffnet
- Ausleihfrist wird eingetragen
  - Enddatum der Ausleihe darf aktuell nicht nach dem 31.12.2099 sein
- Zubehör wird in Notiz-Feld hinterlegt
- Ausleihzettel wird generiert und ausgedruckt
  - Einstellungen für den Druck: beidseitiger Druck, Kopf- und Fuzßzeilen drucken, Hintergrund drucken
- Ausleihzettel: Ausfertigung für Ausleihenden wird übergeben
- Ausleihzettel: Ausfertigung für Institut wird von Ausleiher*in sowie Mitarbeiter unterschrieben
- Gerät wird übergeben
- Unterschriebener Ausleihzettel wird abgeheftet

### Gerät wird während der Ausleihe editiert

- Raumänderungen eines verliehenen Gerätes werden in der Verleihansicht des Gerätes vorgenommen

## Gerät wird zurückgegeben

- Gerät-Ausleihe wird in DLCDB geöffnet
- Rückgabedatum wird eingetragen
- Datensatz wird gespeichert

:::{tip}
Für zurückgegebene Devices wird automatisch ein `INROOM`-Record mit dem definiteren Auto-Return-Room erstellt. Der Auto-Return-Raum wird (einmalig) in der Raumverwaltung definiert.
:::

:::{note}
Als Erweiterung des Ausleihzettels können weitere Seiten ausgegeben/generiert werden. Der Inhalt dieser weiteren Seiten ist frei edierbar (Markdown wird unterstützt). Diese Erweiterung ist über die Ansicht *Verleihen > Checklist* zu erreichen.
:::
