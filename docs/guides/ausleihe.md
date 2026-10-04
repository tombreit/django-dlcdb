# Ausleihe

Die Verleihansicht ist über den Menüpunkt *Ausleihe* im Hauptmenü
erreichbar. Der druckbare Ausleihzettel wird aus der Detailansicht einer
Ausleihe generiert.

:::{tip}
In der Verleihansicht werden nur Geräte aufgeführt, für die die Markierung *Ist verleihbar?* gesetzt ist.
:::

![Verleihansicht](/_static/lending-index.webp){.sd-card}

## Features

- Druckbarer, gebrandeter Ausleihvertrag, inklusive Version für die Ausleihenden
- Editierbare Checkliste als Anhang zum Ausleihvertrag
- Automatische [Erinnerungen](notifications.md) an Ausleiher bei überfälliger Rückgabe

## Gerät wird ausgeliehen

:::{note}
Auch ein verliehenes Gerät hat einen Raum: den, in dem es voraussichtlich zu finden ist. Ist das unklar (z.B. Homeoffice), den [Extern-Raum](erste_schritte.md#6-räume-anlegen) angeben.
:::

- Gerät-Ausleihe wird in DLCDB geöffnet
- Ausleihfrist wird eingetragen
  - Enddatum der Ausleihe darf aktuell nicht nach dem 31.12.2099 sein
- Zubehör wird in Notiz-Feld hinterlegt
- Ausleihzettel wird generiert und ausgedruckt
  - Einstellungen für den Druck: beidseitiger Druck, Kopf- und Fußzeilen drucken, Hintergrund drucken
- Ausleihzettel: Ausfertigung für Ausleihenden wird übergeben
- Ausleihzettel: Ausfertigung für Institut wird von Ausleiher*in sowie Mitarbeiter unterschrieben
- Gerät wird übergeben
- Unterschriebener Ausleihzettel wird abgeheftet

Den Raum eines verliehenen Geräts ändert man in der Ausleihe oder über [Umziehen](umziehen.md#verliehene-geräte); der Verleih läuft dabei weiter.

## Gerät wird zurückgegeben

- Gerät-Ausleihe wird in DLCDB geöffnet
- Rückgabedatum wird eingetragen
- Datensatz wird gespeichert

:::{tip}
Ein zurückgegebenes Gerät kommt automatisch in den [„Auto return“-Raum](erste_schritte.md#6-räume-anlegen).
:::

:::{note}
Als Erweiterung des Ausleihzettels können weitere Seiten ausgegeben/generiert werden. Der Inhalt dieser weiteren Seiten ist frei editierbar (Markdown wird unterstützt). Diese Erweiterung wird im Ausleih-Profil gepflegt: *Einstellungen › Ausleih-Profile*, Feld *Checkliste*.
:::
