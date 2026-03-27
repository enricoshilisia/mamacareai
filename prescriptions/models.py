import uuid
from django.db import models


class Prescription(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation   = models.OneToOneField(
                         'consultations.Consultation', on_delete=models.CASCADE,
                         related_name='prescription')
    created_by     = models.ForeignKey(
                         'mothers.Mother', on_delete=models.CASCADE,
                         related_name='prescriptions_written')
    notes          = models.TextField(blank=True)
    confirmed_at   = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rx – {self.consultation}"

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None


class PrescriptionItem(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug_name    = models.CharField(max_length=200)
    dosage       = models.CharField(max_length=100)
    frequency    = models.CharField(max_length=100)
    duration     = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    ai_suggested = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.drug_name} {self.dosage}"
