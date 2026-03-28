from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Mother, Child


class ChildInline(admin.TabularInline):
    model = Child
    extra = 0
    fields = ("name", "date_of_birth", "gender", "blood_group", "is_active")
    readonly_fields = ("date_of_birth",)


@admin.register(Mother)
class MotherAdmin(UserAdmin):
    list_display  = ("full_name", "phone_number", "email", "city", "country", "is_active", "is_doctor", "date_joined")
    list_filter   = ("is_active", "is_doctor", "country")
    search_fields = ("full_name", "phone_number", "email", "city")
    ordering      = ("-date_joined",)
    inlines       = [ChildInline]

    fieldsets = (
        (None,           {"fields": ("phone_number", "password")}),
        ("Personal",     {"fields": ("full_name", "email", "profile_photo")}),
        ("Location",     {"fields": ("city", "country")}),
        ("Emergency",    {"fields": ("emergency_contact_name", "emergency_contact_phone", "emergency_contact_relationship")}),
        ("Permissions",  {"fields": ("is_active", "is_staff", "is_doctor", "is_superuser", "groups", "user_permissions")}),
        ("Dates",        {"fields": ("date_joined",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone_number", "full_name", "password1", "password2", "is_active", "is_doctor"),
        }),
    )
    readonly_fields = ("date_joined",)


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display  = ("name", "mother", "gender", "blood_group", "date_of_birth", "is_active")
    list_filter   = ("gender", "blood_group", "is_active")
    search_fields = ("name", "mother__full_name", "mother__phone_number")
    ordering      = ("mother__full_name", "date_of_birth")
    raw_id_fields = ("mother",)
