from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid


class MotherManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("Phone number is required")
        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone_number, password, **extra_fields)


class Mother(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to="mothers/photos/", blank=True, null=True)

    # Emergency contact
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True)

    # Location (optional, for nearby services)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Kenya")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_doctor = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    objects = MotherManager()

    class Meta:
        verbose_name = "Mother"
        verbose_name_plural = "Mothers"

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""


class Child(models.Model):
    GENDER_CHOICES = [
        ("M", "Boy"),
        ("F", "Girl"),
        ("U", "Prefer not to say"),
    ]

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"),
        ("B+", "B+"), ("B-", "B-"),
        ("AB+", "AB+"), ("AB-", "AB-"),
        ("O+", "O+"), ("O-", "O-"),
        ("unknown", "Unknown"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mother = models.ForeignKey(Mother, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default="U")
    photo = models.ImageField(upload_to="children/photos/", blank=True, null=True)

    # Health basics
    blood_group = models.CharField(max_length=10, choices=BLOOD_GROUP_CHOICES, default="unknown")
    birth_weight_kg = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    birth_hospital = models.CharField(max_length=200, blank=True)
    pediatrician_name = models.CharField(max_length=150, blank=True)
    pediatrician_phone = models.CharField(max_length=20, blank=True)

    # Allergies / special notes
    allergies = models.TextField(blank=True, help_text="Known allergies or special conditions")
    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Child"
        verbose_name_plural = "Children"
        ordering = ["date_of_birth"]

    def __str__(self):
        return f"{self.name} (child of {self.mother.full_name})"

    @property
    def age_in_days(self):
        return (timezone.now().date() - self.date_of_birth).days

    @property
    def age_display(self):
        days = self.age_in_days
        if days < 7:
            return f"{days} day{'s' if days != 1 else ''} old"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} old"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months != 1 else ''} old"
        else:
            years = days // 365
            months = (days % 365) // 30
            if months:
                return f"{years}y {months}m old"
            return f"{years} year{'s' if years != 1 else ''} old"

    @property
    def gender_display(self):
        return "Boy" if self.gender == "M" else "Girl" if self.gender == "F" else "Baby"