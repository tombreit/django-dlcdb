==========
Ausmustern
==========

Ziel
====

Geräte, die nicht mehr existieren, verschrottet oder verkauft sind in der DLCDB kenntlich machen. Hierzu müssen die Geräte bzw. Records identifiziert (gesucht) werden und deren Status entsprechend gesetzt werden.


Prozess
=======

RecordAdmin
---------------

URL: https://dlcdb-it.mpicc.de/admin/core/record/

.. note:: Bulk-Entfernen
   Über diesen Admin ist ein "Massen-Entfernen" (mehrere Geräte auf einmal) möglich. Alternativ steht noch die `CSV-Bulk-Removal`_ Methode zur Verfügung.


#. Gewünschte Records suchen. Die Filter ``is_active`` und ``Raum`` können hierbei helfen.
#. Gewünschte Records markieren (Checkbox in erster Spalte).
#. Admin-Action in Dropdown-Menü auswählen und ausführen.



RemovedRecordAdmin
----------------------

URL: https://dlcdb-it.mpicc.de/admin/core/removedrecord/


CSV-Bulk-Removal
--------------------

* Es sollen viele Devices auf einmal entfernt/ausgemustert werden.
* Diese Devices werden in einer CSV-Datei mit eventuell weiteren Attributen erfasst.

  * *Hinweis:* Eine existierende CSV-Removal-Datai nutzen und mit neuen Daten füllen.
* Die CSV-Datei wird von der DLCDB eingelesen und die entsprechende Aktion (Record auf "REMOVED" setzen) wird für alle Devices ausgeführt.
* Die DLCDB git eine Zusammenfassung der Vorgänge aus.


Ausbuchung
---------------

Die Ausbuchung muss der Verwaltung mitgeteilt werden: 

See :download:`Ausbuchungsbeleg_Anlagen.docx </_static/Ausbuchungsbeleg_Anlagen.docx>`.

Die Ausgaben der DLCDB (Log-Dateien, generierte CSV-Reports) können als Anlage zu dem Formular genutzt werden, um nicht jedes Device einzeln melden zu müssen.
