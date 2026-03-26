from django.db import models
import uuid


class CryAnalysis(models.Model):

    CRY_TYPES = [
        ("hungry",     "Hungry"),
        ("belly_pain", "Belly Pain"),
        ("burping",    "Burping"),
        ("cold_hot",   "Cold / Hot"),
        ("discomfort", "Discomfort"),
        ("lonely",     "Lonely"),
        ("scared",     "Scared"),
        ("tired",      "Tired"),
        ("unknown",    "Unknown"),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mother           = models.ForeignKey("mothers.Mother",  on_delete=models.CASCADE, related_name="cry_analyses")
    child            = models.ForeignKey("mothers.Child",   on_delete=models.SET_NULL, null=True, blank=True, related_name="cry_analyses")

    # Uploaded audio
    audio_file       = models.FileField(upload_to="cry_recordings/%Y/%m/")
    duration_seconds = models.FloatField(null=True, blank=True)

    # Classification result
    cry_type         = models.CharField(max_length=20, choices=CRY_TYPES, blank=True)
    confidence       = models.FloatField(null=True, blank=True, help_text="0.0 – 1.0")

    # All class probabilities stored as JSON string
    all_probabilities = models.JSONField(null=True, blank=True)

    # AI-generated guidance from GPT
    guidance         = models.TextField(blank=True)

    # If serious, flag it
    is_serious       = models.BooleanField(default=False)

    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Cry Analysis"
        verbose_name_plural = "Cry Analyses"

    def __str__(self):
        child_name = self.child.name if self.child else "Unknown"
        return f"{child_name} — {self.cry_type} ({self.created_at:%d %b %Y %H:%M})"

    @property
    def confidence_percent(self):
        if self.confidence is not None:
            return round(self.confidence * 100, 1)
        return None