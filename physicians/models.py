from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import math


class Physician(models.Model):

    SPECIALIZATION_CHOICES = [
        ("pediatrician",  "Pediatrician"),
        ("neonatologist", "Neonatologist"),
        ("gp",            "General Practitioner"),
        ("lactation",     "Lactation Consultant"),
        ("nutritionist",  "Pediatric Nutritionist"),
    ]

    STATUS_CHOICES = [
        ("pending",   "Pending Approval"),
        ("approved",  "Approved"),
        ("suspended", "Suspended"),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name      = models.CharField(max_length=200)
    specialization = models.CharField(max_length=30, choices=SPECIALIZATION_CHOICES)
    hospital       = models.CharField(max_length=255)
    phone          = models.CharField(max_length=20)
    email          = models.EmailField(blank=True)
    bio            = models.TextField(blank=True)
    photo          = models.ImageField(upload_to="physicians/", null=True, blank=True)

    # Location
    latitude       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    city           = models.CharField(max_length=100)
    country        = models.CharField(max_length=100, default="Kenya")
    address        = models.CharField(max_length=300, blank=True)

    # Status
    status         = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    is_available   = models.BooleanField(default=True)

    # Rating (auto-computed from reviews)
    rating         = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count   = models.PositiveIntegerField(default=0)

    # Linked user account
    user = models.OneToOneField(
        "mothers.Mother", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="physician_profile"
    )

    # If doctor registered themselves
    registered_by_doctor = models.BooleanField(default=False)
    registration_email   = models.EmailField(blank=True)
    registration_notes   = models.TextField(blank=True)

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-rating", "full_name"]
        verbose_name = "Physician"
        verbose_name_plural = "Physicians"

    def __str__(self):
        return f"Dr. {self.full_name} — {self.get_specialization_display()}"

    def update_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        count   = reviews.count()
        if count > 0:
            avg = reviews.aggregate(models.Avg("rating"))["rating__avg"]
            self.rating       = round(avg, 2)
            self.review_count = count
        else:
            self.rating       = 0.00
            self.review_count = 0
        self.save(update_fields=["rating", "review_count"])

    def distance_from(self, lat, lon) -> float:
        """Haversine distance in km from given coordinates."""
        if not self.latitude or not self.longitude:
            return float('inf')
        R    = 6371
        lat1 = math.radians(float(self.latitude))
        lat2 = math.radians(float(lat))
        dlat = math.radians(float(lat) - float(self.latitude))
        dlon = math.radians(float(lon) - float(self.longitude))
        a    = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


class PhysicianReview(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    physician   = models.ForeignKey(Physician, on_delete=models.CASCADE, related_name="reviews")
    mother      = models.ForeignKey("mothers.Mother", on_delete=models.CASCADE, related_name="physician_reviews")
    rating      = models.PositiveSmallIntegerField(
                      validators=[MinValueValidator(1), MaxValueValidator(5)]
                  )
    comment     = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("physician", "mother")
        ordering        = ["-created_at"]

    def __str__(self):
        return f"{self.mother} → Dr. {self.physician.full_name} ({self.rating}★)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.physician.update_rating()


class PhysicianRegistrationRequest(models.Model):
    """Doctors fill this form to request listing on MamaCare."""
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name       = models.CharField(max_length=200)
    specialization  = models.CharField(max_length=30, choices=Physician.SPECIALIZATION_CHOICES)
    hospital        = models.CharField(max_length=255)
    phone           = models.CharField(max_length=20)
    email           = models.EmailField()
    country         = models.CharField(max_length=100, default="Kenya")
    city            = models.CharField(max_length=100)
    bio             = models.TextField(blank=True)
    license_number  = models.CharField(max_length=50, blank=True)
    notes           = models.TextField(blank=True, help_text="Any additional info")
    user            = models.OneToOneField(
                          "mothers.Mother", null=True, blank=True,
                          on_delete=models.SET_NULL, related_name="registration_request"
                      )
    status          = models.CharField(
                          max_length=15,
                          choices=[("pending","Pending"),("approved","Approved"),("rejected","Rejected")],
                          default="pending"
                      )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request: Dr. {self.full_name} ({self.status})"