# Management commands

Most management commands come with a descriptive help message.

List all management commands:

```sh
./manage.py
```

Get help for a specific command:

```sh
./manage.py <command> --help
```

## DLCDB commands

| Command | Does |
|---|---|
| `anonymize_data` | Replace person and device data with random values (for demo/dev copies) |
| `audit_field_losses` | Report device field values that were silently lost on save, optionally restore them |
| `audit_transitions` | Report device record chains that violate the lifecycle transition table |
| `fix_record_modified_at_timestamps` | Repair the `modified_at` timestamp of records |
| `mark_not_handled_assets_in_csv` | Take a CSV file and mark every row that exists in this DLCDB |
| `populate_devicetype_icons` | Pre-populate `DeviceType.icon` with a fitting Bootstrap Icons class |
| `udb_sync_persons` | Run the HR API sync once (see [HR-Sync](hr-sync.md)) |
| `generate_qrcodes` | (Re-)generate the QR codes of every device and room |
| `verify_lendings` | Email lenders about lent devices without a current inventory stamp, or write a report (see [Inventur](../guides/inventur.md)) |
| `fix_inventory_lost_lendings` | Repair `LENT` records that were erroneously turned into `LOST` records |
| `fix_inventory_room_note_pk` | Repair devices inventorized against a note pk instead of a room pk |
