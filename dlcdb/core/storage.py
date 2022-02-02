from django.core.files.storage import FileSystemStorage


class OverwriteStorage(FileSystemStorage):
    """
    Do not append random chars for saving as a new filename, instead delete
    the existent file and return now unused filename.
    """

    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return name
