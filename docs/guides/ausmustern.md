# Ausmustern

## Ziel

Geräte, die nicht mehr existieren, verschrottet oder verkauft sind, sind in der DLCDB kenntlich zu machen. Hierzu müssen die Geräte bzw. Records identifiziert (gesucht) werden und deren Status entsprechend gesetzt werden.

```{admonition} Verwaltungsakt
:class: warning

Ausmustern ist ein "Verwaltungsakt", daher dient diese Doku nur der Inspiration und ist rechtlich nicht belastbar. Bei Fragen/Unklarheiten etc. ist die Finanzabteilung die Ansprechpartnerin.
```

## Einzelnes Gerät ausmustern

1. Gerät in der Geräte-Übersicht (*Hauptmenü › Geräte*) aufrufen
1. Dropdown-Eintrag "Entfernt" auswählen
1. Verbleib nach Ausmusterung via Dropdown angeben (verkauft, verschrottet, …)
1. Notiz (*removed_info*) angeben: z.B. "veraltet", "Speichermedium sicher gelöscht" etc.

## CSV-Bulk-Ausmusterung

Sollen viele Devices auf einmal entfernt/ausgemustert werden:

* Die auszumusternden Devices werden in einer CSV-Datei mit eventuell weiteren Attributen erfasst.
  * *Hinweis:* Eine existierende CSV-Removal-Datei nutzen und mit neuen Daten füllen.
* Die CSV-Datei wird unter *Prozesse › Bulk Ausmusterung* hochgeladen. Die DLCDB liest die Datei ein und führt die entsprechende Aktion (Record auf "ENTFERNT" setzen) für alle Devices aus.
* Die DLCDB gibt eine Zusammenfassung der Vorgänge aus.

:::{note}
**Fallback Django-Admin:** Ein Massen-Entfernen ist alternativ auch über
den Record-Admin (Records markieren, Admin-Action ausführen) möglich.
Bereits ausgemusterte Geräte sind unter *Datenhaltung ›
Entfernt-Records* einsehbar.
:::
