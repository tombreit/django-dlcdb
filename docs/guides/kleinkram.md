# Kleinkram

Ausleihe für z.B. geringwertige Wirtschaftsgüter wie Webcams, Mäuse etc., die nicht als einzelne Devices geführt werden.

Ausleihbare Gerätegattungen werden im Django-Admin gepflegt: *Start › Smallstuff › Things*.

Der Verleih dieser Gegenstände erfolgt im Frontend über den Navigationspunkt *Kleinkram*. Benötigte Berechtigungen (siehe [Berechtigungen](berechtigungen.md#navigation)):

| Vorgang | codename |
|---|---|
| Ansicht öffnen | `smallstuff.view_assignedthing` |
| Gegenstand ausgeben | `smallstuff.add_assignedthing` |
| Gegenstand zurücknehmen | `smallstuff.change_assignedthing` |
