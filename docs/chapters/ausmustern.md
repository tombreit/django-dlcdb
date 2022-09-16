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

```{admonition} Inventurverantwortlich
:class: warning

Das Ausbuchen sollte vom Inventurverantwortlichen durchgeführt werden. Bei Fragen oder Unklarheiten ist in jedem Fall der oder die Inventurverantwortliche zu kontaktieren.
```

## Ausgangslage/Prosa


Geräte sind defekt/nicht reparabel, veraltet oder können aus sonstigen Gründen vom Institut nicht mehr genutzt werden. Solche Geräte sollen "ausgemustert" werden. Dies geschieht zum Einen in der DLCDB, zum Anderen in der Anlangebuchhaltung der Verwaltung. 

Beim Ausmustern sind einige Regeln zu beachten; Kurzform: 

1. Schriftform einhalten: Formulare ausfüllen, Anhänge ausdrucken etc.
1. Ausmusterungsgrund muss vorliegen
1. Gerät muss beschrieben werden
1. bei Defekt:

   - verschrotten

1. ohne Defekt (veraltet, nicht mehr benötigt etc.):

   - Gerät muss über die MPG-Einkäuferliste anderen Instituten angeboten werden. Diese Meldung übernimmt die Einkaufsabteilung.
   - Ab bestimmten Wertgrenzen ist ein Verkauf über eine Verwertungsgesellschaft notwendig (falls kein Institut Interesse angemeldet hat)



## Prozess

### Ausbuchung DLCDB

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


### Ausbuchung Verwaltung

Die Ausbuchung muss der Verwaltung mitgeteilt werden: 

Via [**Ausbuchungsbeleg_Anlagen.docx**](../_static/Ausbuchungsbeleg_Anlagen.docx)

Beim Ausbuchen von mehreren Geräten ("Bulk-Entfernen") können die Ausgaben der DLCDB (Log-Dateien, generierte CSV-Reports) als Anlage zu dem Formular genutzt werden, um nicht jedes Device einzeln melden zu müssen.

Der Ausbuchungsbeleg ist dem Inventurverantwortlichen oder dem Abteilungsleiter zur Unterschrift vorzulegen und wird dann an die Verwaltung, Abteilung Finanzen, weitergeleitet.
