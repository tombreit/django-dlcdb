# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.core.files.storage import FileSystemStorage


class OverwriteStorage(FileSystemStorage):
    """
    Do not append random chars for saving as a new filename, instead delete
    the existent file and return now unused filename.

    No field uses it any more (it stored the QR codes), but the migrations
    import it.
    """

    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return name
