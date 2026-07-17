# Welcome to DLCDB's documentation.

Die DLCDB verwaltet den Lebenszyklus von IT-Assets: Jedes Gerät sammelt
eine Kette von Zustandseinträgen (*Records*) — von der Lokalisierung
über Verleih und Inventur bis zur Ausmusterung. Daraus ergibt sich eine
lückenlose Historie ganz von selbst. Betrieben wird das Ganze mit einem
bewusst einfachen Stack: Django, SQLite, server-gerendertes UI.

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

:::{grid-item-card} {octicon}`rocket;1.5em;sd-me-1` Setup
:link: betrieb/setup
:link-type: doc

Die DLCDB ist ein Django-Projekt und ist schnell und einfach aufgesetzt.

+++
[Setup »](betrieb/setup)
:::

::::

`````{dropdown} Inhaltsverzeichnis
:icon: book
:color: light

```{toctree}
:maxdepth: 3

konzept
guides/index
betrieb/index
faq
```

`````

Verbesserungsvorschläge, Fehler gefunden, Kommentare?
[📧 Thomas Breitner](mailto:t.breitner@csl.mpg.de)

![Dashboard](/_static/dashboard.webp){.sd-card}
