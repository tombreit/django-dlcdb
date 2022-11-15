# Ausmustern

<style>
/* Experimenting with styles from 
   https://myst-parser.readthedocs.io/en/latest/
*/


details {
    margin-bottom: 0.5em;
}

summary {
    margin-bottom: 1em;
    font-size: larger;
    font-weight: bold; 
}

</style>


## Ziel

Geräte, die nicht mehr existieren, verschrottet oder verkauft sind sind in der DLCDB kenntlich zu machen. Hierzu müssen die Geräte bzw. Records identifiziert (gesucht) werden und deren Status entsprechend gesetzt werden.


```{admonition} Verwaltungsakt
:class: warning

Ausmustern ist ein "Verwaltungsakt", daher dient diese Doku nur der Inspiration und ist rechtlich nicht belastbar. Bei Fragen/Unklarheite etc. ist die Finazabteilung die Ansprechpartnerin.
```

## Prozess

<details>
<summary>Device</summary>

URL: https://fqdn/admin/core/device/

1. Device-Seite aufrufen
1. Dropdown Eintrag "Entfernt" auswählen
1. Verbleib nach Ausmusterung via Dropdown angeben
1. Notiz (*removed_info*) angeben: z.B. "veraltet", "Speichermedium sicher gelöscht" etc.

</details>


<details>
<summary>RecordAdmin</summary>

URL: https://fqdn/admin/core/record/

```{admonition} Bulk-Removal
:class: note

   Über diesen Admin ist ein "Massen-Entfernen" (mehrere Geräte auf einmal) möglich. Alternativ steht noch die `CSV-Bulk-Removal`_ Methode zur Verfügung.
```

1. Gewünschte Records suchen. Die Filter ``is_active`` und ``Raum`` können hierbei helfen.
1. Gewünschte Records markieren (Checkbox in erster Spalte).
1. Admin-Action in Dropdown-Menü auswählen und ausführen.

</details>


<details>
<summary>RemovedRecordAdmin</summary>

URL: https://fqdn/admin/core/removedrecord/

</details>

<details>
<summary>CSV-Bulk-Removal</summary>


* Es sollen viele Devices auf einmal entfernt/ausgemustert werden.
* Diese Devices werden in einer CSV-Datei mit eventuell weiteren Attributen erfasst.

  * *Hinweis:* Eine existierende CSV-Removal-Datai nutzen und mit neuen Daten füllen.
* Die CSV-Datei wird von der DLCDB eingelesen und die entsprechende Aktion (Record auf "REMOVED" setzen) wird für alle Devices ausgeführt.
* Die DLCDB git eine Zusammenfassung der Vorgänge aus.

</details>
