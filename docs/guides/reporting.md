# Reporting

Die App `dlcdb.reporting` erzeugt Report-Artefakte: tabellarische Übersichten
über Records als xlsx-Spreadsheet und Text-Repräsentation, gespeichert als
`Report` (Titel, Body, Spreadsheet-Datei unter
`media/reporting/spreadsheets/`).

Welche Felder in Reports auftauchen, steuert `EXPOSED_FIELDS` in
`dlcdb/reporting/settings.py` (pro Record-Typ).

Reports werden über `dlcdb.reporting.services.create_report()` erzeugt —
in der Regel durch die Subscriptions der Notifications-App, die die Reports
per Email mit xlsx-Anhang versendet (siehe [](notifications.md)).
Erzeugte Reports sind im Django-Admin einsehbar (read-only).
