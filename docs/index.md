---
html_theme.sidebar_secondary.remove: true
---

# DLCDB-Dokumentation

Die DLCDB verwaltet den Lebenszyklus von IT-Assets, von der Bestellung
über Verleih und Inventur bis zur Ausmusterung.

::::{grid} 1 2 2 3
:gutter: 1 1 1 2

:::{grid-item-card} {octicon}`light-bulb;1.5em;sd-me-1` Konzept
:link: konzept
:link-type: doc

Devices, Records, Audit-Trail: die Architektur der DLCDB in fünf Minuten.

+++
[Konzept »](konzept)
:::

:::{grid-item-card} {octicon}`heart;1.5em;sd-me-1` Erste Schritte
:link: guides/erste_schritte
:link-type: doc

Beginne deine IT-Assets/Devices mit der DLCDB zu verwalten.

+++
[Erste Schritte »](guides/erste_schritte)
:::

:::{grid-item-card} {octicon}`device-desktop;1.5em;sd-me-1` Geräte
:link: guides/devices
:link-type: doc

Die zentrale Geräteverwaltung: Übersicht, Detailseite und Zustände.

+++
[Geräte »](guides/devices)
:::

:::{grid-item-card} {octicon}`rocket;1.5em;sd-me-1` Setup
:link: betrieb/setup
:link-type: doc

Die DLCDB ist ein Django-Projekt und ist schnell und einfach aufgesetzt.

+++
[Setup »](betrieb/setup)
:::

::::

## Konzept

Devices, Records und Audit-Trail: wie die DLCDB den Lebenszyklus eines Geräts abbildet.

```{toctree}
:maxdepth: 2

konzept
```

## Guides

Einrichtung und tägliche Arbeit mit der DLCDB.

```{toctree}
:maxdepth: 2

guides/index
```

## Betrieb

Installation, Datenmodell und Schnittstellen.

```{toctree}
:maxdepth: 2

betrieb/index
```

## FAQ

```{toctree}
:maxdepth: 2

faq
```

Verbesserungsvorschläge, Fehler gefunden, Kommentare?
[📧 Thomas Breitner](mailto:t.breitner@csl.mpg.de)
