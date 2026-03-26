from django.contrib import admin
from .models import Physician, PhysicianReview, PhysicianRegistrationRequest


@admin.register(Physician)
class PhysicianAdmin(admin.ModelAdmin):
    list_display  = ["full_name", "specialization", "hospital", "city", "status", "rating", "is_available"]
    list_filter   = ["status", "specialization", "is_available", "city"]
    search_fields = ["full_name", "hospital", "city", "email"]
    list_editable = ["status", "is_available"]
    readonly_fields = ["rating", "review_count", "created_at", "updated_at"]

    fieldsets = (
        ("Basic Info", {
            "fields": ("full_name", "specialization", "hospital", "phone", "email", "bio", "photo")
        }),
        ("Location", {
            "fields": ("address", "city", "country", "latitude", "longitude")
        }),
        ("Status", {
            "fields": ("status", "is_available", "registered_by_doctor", "registration_email", "registration_notes")
        }),
        ("Stats (auto-computed)", {
            "fields": ("rating", "review_count"),
            "classes": ("collapse",)
        }),
    )

    actions = ["approve_physicians", "suspend_physicians"]

    def approve_physicians(self, request, queryset):
        queryset.update(status="approved")
        self.message_user(request, f"{queryset.count()} physician(s) approved.")
    approve_physicians.short_description = "Approve selected physicians"

    def suspend_physicians(self, request, queryset):
        queryset.update(status="suspended")
        self.message_user(request, f"{queryset.count()} physician(s) suspended.")
    suspend_physicians.short_description = "Suspend selected physicians"


@admin.register(PhysicianReview)
class PhysicianReviewAdmin(admin.ModelAdmin):
    list_display  = ["physician", "mother", "rating", "is_approved", "created_at"]
    list_filter   = ["is_approved", "rating"]
    list_editable = ["is_approved"]
    search_fields = ["physician__full_name", "mother__full_name"]


@admin.register(PhysicianRegistrationRequest)
class PhysicianRegistrationRequestAdmin(admin.ModelAdmin):
    list_display  = ["full_name", "specialization", "hospital", "city", "email", "status", "created_at"]
    list_filter   = ["status", "specialization"]
    search_fields = ["full_name", "hospital", "email"]
    list_editable = ["status"]
    readonly_fields = ["created_at"]

    actions = ["approve_and_create_physician"]

    def approve_and_create_physician(self, request, queryset):
        created = 0
        for req in queryset:
            physician, was_created = Physician.objects.get_or_create(
                email=req.email,
                defaults=dict(
                    full_name             = req.full_name,
                    specialization        = req.specialization,
                    hospital              = req.hospital,
                    phone                 = req.phone,
                    city                  = req.city,
                    bio                   = req.bio,
                    status                = "approved",
                    registered_by_doctor  = True,
                    registration_email    = req.email,
                    registration_notes    = req.notes,
                    user                  = req.user,
                )
            )
            # Activate the linked user account
            if req.user and not req.user.is_active:
                req.user.is_active = True
                req.user.save(update_fields=["is_active"])

            # Link user to physician if not already set
            if req.user and not physician.user:
                physician.user = req.user
                physician.save(update_fields=["user"])

            req.status = "approved"
            req.save()
            if was_created:
                created += 1
        self.message_user(request, f"{created} physician profile(s) created and approved.")
    approve_and_create_physician.short_description = "Approve and create physician profiles"