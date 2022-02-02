========
Ausleihe
========


Spezielle Ansicht zum Management des Verleih-Prozesses:

* Devices verleihen
* Ausgeliehene Devices entgegennehmen
* In ChangeList sollten nur ausgeliehene oder verleibare Devices ausgeführt werden


Prozess
=======


Gerät wird ausgeliehen
----------------------

* Gerät-Ausleihe wird in DLCDB geöffnet
* Ausleihfrist wird eingetragen

  * Enddatum der Ausleihe darf aktuell nicht nach dem 31.12.2099 sein
 
* Zubehör wird in Notiz-Feld hinterlegt
* Ausleihzettel wird generiert und ausgedruckt
* Ausleihzettel wird unterschrieben
* Gerät wird übergeben


Gerät wird zurückgegeben
------------------------

* Gerät-Ausleihe wird in DLCDB geöffnet
* Rückgabedatum wird eingetragen
* Datensatz wird gespeichert


Use Cases
=========

* Frist verlängern
* Gerät zurückgeben
* Funktionsprüfung
* Was soll mit den Daten passieren
* Nicht fristgerecht Rot markiert (Überfällige Geräte sollen ersichtlich sein)
