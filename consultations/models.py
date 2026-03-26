import uuid
from django.db import models


class Consultation(models.Model):
    SEVERITY_CHOICES = [
        ("mild",     "Mild"),
        ("moderate", "Moderate"),
        ("severe",   "Severe"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("accepted",  "Accepted"),
        ("declined",  "Declined"),
        ("completed", "Completed"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mother       = models.ForeignKey(
                       "mothers.Mother", on_delete=models.CASCADE,
                       related_name="consultations"
                   )
    physician    = models.ForeignKey(
                       "physicians.Physician", on_delete=models.CASCADE,
                       related_name="consultations"
                   )
    child        = models.ForeignKey(
                       "mothers.Child", on_delete=models.SET_NULL,
                       null=True, blank=True, related_name="consultations"
                   )
    conversation = models.ForeignKey(
                       "chat.Conversation", on_delete=models.SET_NULL,
                       null=True, blank=True, related_name="consultations"
                   )
    symptoms     = models.TextField(help_text="Summary of symptoms from AI assessment")
    severity     = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    specialist   = models.CharField(max_length=30, blank=True, help_text="e.g. pediatrician")
    ai_summary   = models.TextField(blank=True, help_text="AI clinical summary generated on accept")
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    mother_lat   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    mother_lon   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Consultation"
        verbose_name_plural = "Consultations"

    def __str__(self):
        child_label = self.child.name if self.child else "General"
        return f"[{self.severity}] {self.mother} → Dr. {self.physician.full_name} ({child_label})"


class ConsultationMessage(models.Model):
    SENDER_CHOICES = [
        ("mother", "Mother"),
        ("doctor", "Doctor"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
                       Consultation, on_delete=models.CASCADE,
                       related_name="messages"
                   )
    sender_type  = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content      = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Consultation Message"
        verbose_name_plural = "Consultation Messages"

    def __str__(self):
        return f"[{self.sender_type}] {self.content[:50]}"
