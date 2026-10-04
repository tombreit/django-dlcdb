# Ausmustern

## Ziel

Geräte, die nicht mehr existieren, verschrottet oder verkauft sind, sind in der DLCDB kenntlich zu machen. Hierzu müssen die Geräte bzw. Records identifiziert (gesucht) werden und deren Status entsprechend gesetzt werden.

```{admonition} Verwaltungsakt
:class: warning

Ausmustern ist ein "Verwaltungsakt", daher dient diese Doku nur der Inspiration und ist rechtlich nicht belastbar. Bei Fragen/Unklarheiten etc. ist die Finanzabteilung die Ansprechpartnerin.
```

## Einzelnes Gerät ausmustern

1. Gerät in der Geräte-Übersicht (*Hauptmenü › Geräte*) aufrufen
1. Auf der Detailseite *Neuer Zustand › Entfernen* wählen. Der Eintrag öffnet ein Formular des Django-Admins (siehe [Frontend oder Django-Admin?](berechtigungen.md#frontend-oder-django-admin))
1. Verbleib nach Ausmusterung via Dropdown angeben (verkauft, verschrottet, …)
1. Notiz (*removed_info*) angeben: z.B. "veraltet", "Speichermedium sicher gelöscht" etc.

## CSV-Bulk-Ausmusterung

Sollen viele Devices auf einmal entfernt/ausgemustert werden:

* Die auszumusternden Devices werden in einer CSV-Datei mit eventuell weiteren Attributen erfasst.
  * *Hinweis:* Eine existierende CSV-Removal-Datei nutzen und mit neuen Daten füllen.
* Die CSV-Datei wird unter *Prozesse › Bulk Ausmusterung* (Django-Admin) hochgeladen. Die DLCDB liest die Datei ein und führt die entsprechende Aktion (Record auf "ENTFERNT" setzen) für alle Devices aus.
  * Gefunden werden nur Devices der eigenen [Mandanten](berechtigungen.md#mandanten); jedes andere Device gilt als nicht vorhanden.
* Die DLCDB gibt eine Zusammenfassung der Vorgänge aus.

Bereits ausgemusterte Geräte listet *Datenhaltung › Entfernt-Records*. *Entfernt* ist standardmäßig ein Endzustand, siehe [Ausmusterung rückgängig machen](berechtigungen.md#statuswechsel).
