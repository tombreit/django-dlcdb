from django.db import models
from ..core.models.abstracts import SingletonBaseModel

class LendingConfiguration(SingletonBaseModel):
    lending_preparation_checklist = models.TextField(
        help_text="Basic Markdown supported. '[ ]' converted to checkbox input."
    )

    def __str__(self):
        return "Lending Configuration"

    class Meta:
        verbose_name = "Lending Configuration"
        verbose_name_plural = "Lending Configuration"
