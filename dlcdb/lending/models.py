# SPDX-FileCopyrightText: 2024 Thomas Breitner
#
# SPDX-License-Identifier: EUPL-1.2

from django.db import models
from ..core.models.abstracts import SingletonBaseModel


class LendingConfigurationRegulation(models.Model):
    lending_configuration = models.ForeignKey("lending.LendingConfiguration", on_delete=models.CASCADE)
    regulation = models.ForeignKey("core.Link", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("lending_configuration", "regulation")

    def __str__(self):
        return f"LendingConfiguration - {self.regulation.linktext}"


class LendingConfiguration(SingletonBaseModel):
    lending_preparation_checklist = models.TextField(
        blank=True, help_text="Basic Markdown supported. '[ ]' converted to checkbox input."
    )
    mandatory_regulations = models.ManyToManyField(
        "core.Link",
        through="lending.LendingConfigurationRegulation",
        related_name="+",
    )

    def __str__(self):
        return "Lending Configuration"

    class Meta:
        verbose_name = "Lending Configuration"
        verbose_name_plural = "Lending Configuration"
