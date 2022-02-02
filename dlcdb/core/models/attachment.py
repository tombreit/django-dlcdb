from django.db import models

from .abstracts import AuditBaseModel


class Attachment(AuditBaseModel):
    title = models.CharField(
        max_length=255,
        blank=False,
    )
    file = models.FileField(
        blank=False,
        upload_to='attachments/',
    )

    def __str__(self):
        if self.created_at:
            selfstring = f"Attachment: '{self.title}' / Created: '{self.created_at:%Y-%m-%d}'"
        else:
            selfstring = f"Attachment: '{self.title}'"

        return selfstring
        
    
    class Meta:
        verbose_name = 'Attachment'
        verbose_name_plural = 'Attachments'
        ordering = ['-created_at']
