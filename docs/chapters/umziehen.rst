========
Umziehen
========

Möglichkeiten
=============

Umzug eines einzelnen Gerätes
-----------------------------

* Umzuziehendes Gerät aufrufen. Such-, Filter- und Sortierfunktionen können bei der Auswahl hilfreich sein.
* Im Dropdown-Menü "Lokalisiert" auswählen.
* Neuen Raum angeben. 
* Neue Raumzuordnung speichern.

**Hinweis**: Ist ein Device aktuell "verliehen" und wird wie oben beschrieben "lokalisiert", wird der aktuelle Verleih damit beendet und ein "InRoomRecord" für dieses Gerät erstellt. Ist eine Raumänderung eines verliehenen Geräts gewünscht, so ist diese in der Verleihansicht des Devices vorzunehmen.


Umzug mehrerer Geräte
---------------------

.. raw:: html

    <div style="text-align: center; margin-bottom: 2em;">
    <iframe width="100%" height="400" src="../_static/relocate.webm" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
    </div>

* "Device-Admin" aufrufen
* Umzuziehende Gerät aufrufen. 

  * Such-, Filter- und Sortierfunktionen können bei der Auswahl hilfreich sein.
  * Die Paginierung kann via "Zeige alle" in der Fußzeile der Gerätetabelle deaktiviert werden.

* Im Django-Admin Actions Dropdown "relocate" auswählen
* Gerätedaten nochmals prüfen.
* Neuen Raum angeben. 
* Button "Relocate devices" anklicken.
