# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from pathlib import Path
import pytest
from django.core.exceptions import ValidationError

from ..utils.bulk_management import import_data
from ..models import ImporterList


@pytest.mark.django_db
def test_bulk_import_csv(tenant):
    csv_path = Path("dlcdb/core/tests/test_data/devices.correct.csv")

    with open(csv_path, "rb") as csv_file:
        assert import_data(
            csv_file,
            importer_inst_pk=None,
            valid_col_headers=ImporterList.VALID_COL_HEADERS,
            import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
            tenant=tenant,
            username="pytestuser",
            write=True,
        )


@pytest.mark.django_db
def test_bulk_import_csv_wrongdate(tenant):
    with pytest.raises(ValueError):
        csv_path = Path("dlcdb/core/tests/test_data/devices.wrongdateformat.csv")

        with open(csv_path, "rb") as csv_file:
            assert import_data(
                csv_file,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                tenant=tenant,
                username="pytestuser",
                write=True,
            )


@pytest.mark.django_db
def test_bulk_import_csv_incomplete_rowheader(tenant):
    with pytest.raises(ValidationError):
        csv_path = Path("dlcdb/core/tests/test_data/devices.incompleterowheader.csv")

        with open(csv_path, "rb") as csv_file:
            assert import_data(
                csv_file,
                importer_inst_pk=None,
                valid_col_headers=ImporterList.VALID_COL_HEADERS,
                import_format=ImporterList.ImportFormatChoices.INTERNALCSV,
                tenant=tenant,
                username="pytestuser",
                write=True,
            )
